from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal, get_db_session
from app.dependencies import get_current_user_id
from app.schemas import MessageCreateRequest, MessageFeedbackRequest, MessageRead, MessageRegenerateRequest
from app.services.embeddings import get_embedding
from app.services.llm import generate_conversation_title, stream_model_response


router = APIRouter(prefix="/conversations/{conversation_id}/messages", tags=["messages"])
messages_action_router = APIRouter(prefix="/messages", tags=["messages"])


async def stream_rag_llm_response(
    *,
    session: AsyncSession,
    conversation_id: UUID,
    user_message_id: UUID,
):
    # 1. Fetch conversation (title only in simplified schema)
    conv_res = await session.execute(
        text("SELECT id FROM conversations WHERE id = :id"),
        {"id": conversation_id},
    )
    if conv_res.mappings().one_or_none() is None:
        raise RuntimeError("Conversation not found during streaming.")

    # 2. Get user message content
    msg_res = await session.execute(
        text("SELECT content FROM messages WHERE id = :id"),
        {"id": user_message_id},
    )
    user_content = msg_res.mappings().one()["content"]

    # 3. Retrieve related chunks scoped to this conversation
    retrieved_chunks: list[dict] = []
    docs_res = await session.execute(
        text(
            "SELECT document_id FROM conversation_documents WHERE conversation_id = :conversation_id"
        ),
        {"conversation_id": conversation_id},
    )
    document_ids = [r["document_id"] for r in docs_res.mappings().all()]

    if document_ids:
        try:
            query_vector = get_embedding(user_content)
            chunks_res = await session.execute(
                text(
                    """
                    SELECT dc.id AS chunk_id, dc.chunk_text,
                           (1.0 - (ce.embedding <=> :query_vector)) AS similarity_score
                    FROM chunk_embeddings ce
                    JOIN document_chunks dc ON dc.id = ce.chunk_id
                    JOIN conversation_documents cd ON cd.document_id = dc.document_id
                    WHERE cd.conversation_id = :conversation_id
                    ORDER BY ce.embedding <=> :query_vector
                    LIMIT 5
                    """
                ),
                {
                    "conversation_id": conversation_id,
                    "query_vector": query_vector,
                },
            )
            for idx, row in enumerate(chunks_res.mappings().all()):
                retrieved_chunks.append(
                    {
                        "chunk_id": row["chunk_id"],
                        "chunk_text": row["chunk_text"],
                        "page_number": None,
                        "similarity_score": float(row["similarity_score"]),
                        "rank": idx + 1,
                    }
                )
        except Exception:
            # Embeddings/provider may be unavailable; continue without RAG context.
            retrieved_chunks = []

    # 4. Build chronological history through the user message
    hist_res = await session.execute(
        text(
            """
            SELECT role, content
            FROM messages
            WHERE conversation_id = :conversation_id
              AND created_at <= (SELECT created_at FROM messages WHERE id = :user_message_id)
            ORDER BY created_at ASC
            """
        ),
        {"conversation_id": conversation_id, "user_message_id": user_message_id},
    )
    history = [{"role": r["role"], "content": r["content"]} for r in hist_res.mappings().all()]

    # 5. Stream model tokens
    assistant_content_chunks: list[str] = []
    async for chunk in stream_model_response(
        "You are a helpful assistant. Prefer using retrieved document context when available.",
        history,
        retrieved_chunks,
        "google/flan-t5-large",
        {},
    ):
        yield chunk
        if chunk.startswith("data: "):
            try:
                payload = json.loads(chunk[6:].strip())
                if "token" in payload:
                    assistant_content_chunks.append(payload["token"])
            except Exception:
                pass

    assistant_reply = "".join(assistant_content_chunks).strip()
    if not assistant_reply:
        assistant_reply = "I could not generate a response right now."

    # 6. Persist assistant reply
    asst_msg_res = await session.execute(
        text(
            """
            INSERT INTO messages (conversation_id, role, content)
            VALUES (:conversation_id, 'assistant', :content)
            RETURNING id
            """
        ),
        {
            "conversation_id": conversation_id,
            "content": assistant_reply,
        },
    )
    asst_msg_id = asst_msg_res.mappings().one()["id"]

    # 7. Auto-title after first exchange
    count_res = await session.execute(
        text("SELECT COUNT(*) AS cnt FROM messages WHERE conversation_id = :conversation_id"),
        {"conversation_id": conversation_id},
    )
    if int(count_res.mappings().one()["cnt"]) == 2:
        new_title = generate_conversation_title(user_content, assistant_reply)
        await session.execute(
            text(
                """
                UPDATE conversations
                SET title = :title, updated_at = now()
                WHERE id = :conversation_id
                """
            ),
            {"title": new_title, "conversation_id": conversation_id},
        )
    else:
        await session.execute(
            text("UPDATE conversations SET updated_at = now() WHERE id = :conversation_id"),
            {"conversation_id": conversation_id},
        )

    await session.commit()

    yield f"data: {json.dumps({'message_id': str(asst_msg_id), 'citations': []})}\n\n"


@router.post("", response_model=None)
async def create_message(
    conversation_id: UUID,
    payload: MessageCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    async with AsyncSessionLocal() as session:
        conv = await session.execute(
            text("SELECT id FROM conversations WHERE id = :id AND user_id = :user_id"),
            {"id": conversation_id, "user_id": user_id},
        )
        if conv.mappings().one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

        user_msg_res = await session.execute(
            text(
                """
                INSERT INTO messages (conversation_id, role, content)
                VALUES (:conversation_id, 'user', :content)
                RETURNING id
                """
            ),
            {
                "conversation_id": conversation_id,
                "content": payload.content,
            },
        )
        user_msg_id = user_msg_res.mappings().one()["id"]
        await session.commit()

    async def sse_generator():
        async with AsyncSessionLocal() as session:
            async for chunk in stream_rag_llm_response(
                session=session,
                conversation_id=conversation_id,
                user_message_id=user_msg_id,
            ):
                yield chunk

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.get("", response_model=list[MessageRead])
async def list_messages(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> list[MessageRead]:
    conv = await session.execute(
        text("SELECT id FROM conversations WHERE id = :id AND user_id = :user_id"),
        {"id": conversation_id, "user_id": user_id},
    )
    if conv.mappings().one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    result = await session.execute(
        text(
            """
            SELECT id, conversation_id, parent_message_id, role, content, model_name,
                   token_count, generation_time, is_helpful, feedback_text, created_at
            FROM messages
            WHERE conversation_id = :conversation_id
            ORDER BY created_at ASC
            """
        ),
        {"conversation_id": conversation_id},
    )
    return [MessageRead.model_validate(row) for row in result.mappings().all()]


@messages_action_router.post("/{message_id}/regenerate", response_model=None)
async def regenerate_message(
    message_id: UUID,
    payload: MessageRegenerateRequest,
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    _ = payload
    async with AsyncSessionLocal() as session:
        msg_res = await session.execute(
            text(
                """
                SELECT m.id, m.conversation_id, m.role, m.content, c.user_id
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE m.id = :message_id
                """
            ),
            {"message_id": message_id},
        )
        msg_row = msg_res.mappings().one_or_none()
        if msg_row is None or str(msg_row["user_id"]) != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

        conversation_id = msg_row["conversation_id"]

        # Re-run generation from the latest user message content if regenerating assistant.
        if msg_row["role"] == "assistant":
            user_msg_res = await session.execute(
                text(
                    """
                    SELECT id
                    FROM messages
                    WHERE conversation_id = :conversation_id
                      AND role = 'user'
                      AND created_at < (
                          SELECT created_at FROM messages WHERE id = :message_id
                      )
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"conversation_id": conversation_id, "message_id": message_id},
            )
            user_msg = user_msg_res.mappings().one_or_none()
            if user_msg is None:
                raise HTTPException(status_code=400, detail="No prior user message to regenerate from.")
            user_msg_id = user_msg["id"]
        else:
            user_msg_id = msg_row["id"]

    async def sse_generator():
        async with AsyncSessionLocal() as session:
            async for chunk in stream_rag_llm_response(
                session=session,
                conversation_id=conversation_id,
                user_message_id=user_msg_id,
            ):
                yield chunk

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@messages_action_router.post("/{message_id}/feedback")
async def submit_feedback(
    message_id: UUID,
    payload: MessageFeedbackRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, str]:
    # Feedback columns were removed from the simplified schema.
    # Keep endpoint for UI compatibility and verify ownership only.
    _ = payload
    result = await session.execute(
        text(
            """
            SELECT m.id
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE m.id = :message_id AND c.user_id = :user_id
            """
        ),
        {"message_id": message_id, "user_id": user_id},
    )
    if result.mappings().one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    return {"status": "ok"}
