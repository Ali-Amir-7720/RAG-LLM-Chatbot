from __future__ import annotations

import json
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal, get_db_session
from app.dependencies import get_current_user_id
from app.schemas import (
    MessageCreateRequest,
    MessageFeedbackRequest,
    MessageRead,
    MessageRegenerateRequest,
)
from app.services.embeddings import get_embedding
from app.services.llm import generate_conversation_title, stream_model_response


# Router for conversation-scoped messages (creation and history retrieval)
router = APIRouter(prefix="/conversations/{conversation_id}/messages", tags=["messages"])

# Router for message-level actions (feedback and regeneration)
messages_action_router = APIRouter(prefix="/messages", tags=["messages"])


async def stream_rag_llm_response(
    *,
    session: AsyncSession,
    conversation_id: UUID,
    user_message_id: UUID,
    parent_message_id: UUID | None,
    user_id: str,
):
    """
    Core RAG-LLM pipeline. Generates text query embeddings, searches the pgvector
    chunk_embeddings database using cosine distance (<=>) for active conversation documents,
    assembles message history, streams token chunks, and saves the final response + citations.
    """
    # 1. Fetch system prompt and model_name for the conversation
    conv_res = await session.execute(
        text(
            "SELECT model_name, system_prompt, generation_config "
            "FROM conversations WHERE id = :id"
        ),
        {"id": conversation_id},
    )
    conv_row = conv_res.mappings().one()
    model_name = conv_row["model_name"]
    system_prompt = conv_row["system_prompt"]
    generation_config = conv_row["generation_config"] or {}

    # 2. Get user message content
    msg_res = await session.execute(
        text("SELECT content FROM messages WHERE id = :id"),
        {"id": user_message_id},
    )
    user_content = msg_res.mappings().one()["content"]

    # 3. Fetch scoped documents
    docs_res = await session.execute(
        text("SELECT document_id FROM conversation_documents WHERE conversation_id = :conversation_id"),
        {"conversation_id": conversation_id},
    )
    document_ids = [r["document_id"] for r in docs_res.mappings().all()]

    retrieved_chunks = []
    embedding_model_id = None
    
    if document_ids:
        # Fetch the active embedding model registration
        em_res = await session.execute(
            text("SELECT id FROM embedding_models ORDER BY created_at ASC LIMIT 1")
        )
        em_row = em_res.mappings().one_or_none()
        
        if em_row:
            embedding_model_id = em_row["id"]
            # Generate query vector
            query_vector = get_embedding(user_content)
            
            # Query relevant chunks from pgvector using <=> (cosine distance)
            chunks_res = await session.execute(
                text(
                    """
                    SELECT dc.id AS chunk_id, dc.chunk_text, dc.page_number,
                           (1.0 - (ce.embedding <=> :query_vector)) AS similarity_score
                    FROM chunk_embeddings ce
                    JOIN document_chunks dc ON dc.id = ce.chunk_id
                    JOIN conversation_documents cd ON cd.document_id = dc.document_id
                    WHERE cd.conversation_id = :conversation_id
                      AND ce.embedding_model_id = :model_id
                    ORDER BY ce.embedding <=> :query_vector
                    LIMIT 5
                    """
                ),
                {
                    "conversation_id": conversation_id,
                    "model_id": embedding_model_id,
                    "query_vector": query_vector,
                },
            )
            raw_chunks = chunks_res.mappings().all()
            for idx, r in enumerate(raw_chunks):
                retrieved_chunks.append({
                    "chunk_id": r["chunk_id"],
                    "chunk_text": r["chunk_text"],
                    "page_number": r["page_number"],
                    "similarity_score": float(r["similarity_score"]),
                    "rank": idx + 1,
                })

    # 4. Fetch chronological history context (including the user message)
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

    # 5. Stream model tokens (Hugging Face integration placeholder)
    start_time = time.time()
    assistant_content_chunks = []
    
    async for chunk in stream_model_response(
        system_prompt,
        history,
        retrieved_chunks,
        model_name,
        generation_config,
    ):
        yield chunk
        if chunk.startswith("data: "):
            try:
                payload = json.loads(chunk[6:].strip())
                if "token" in payload:
                    assistant_content_chunks.append(payload["token"])
            except Exception:
                pass

    assistant_reply = "".join(assistant_content_chunks)
    generation_time = time.time() - start_time
    token_count = max(1, len(assistant_reply) // 4)  # Simple token estimation

    # 6. Save assistant reply in database
    asst_msg_res = await session.execute(
        text(
            """
            INSERT INTO messages (conversation_id, parent_message_id, role, content, model_name, token_count, generation_time)
            VALUES (:conversation_id, :parent_message_id, 'assistant', :content, :model_name, :token_count, :generation_time)
            RETURNING id
            """
        ),
        {
            "conversation_id": conversation_id,
            "parent_message_id": user_message_id,
            "content": assistant_reply,
            "model_name": model_name,
            "token_count": token_count,
            "generation_time": generation_time,
        },
    )
    asst_msg_id = asst_msg_res.mappings().one()["id"]

    # 7. Save RAG citations
    citations_data = []
    if retrieved_chunks and embedding_model_id is not None:
        for chunk in retrieved_chunks:
            await session.execute(
                text(
                    """
                    INSERT INTO message_citations (message_id, chunk_id, embedding_model_id, similarity_score, rank)
                    VALUES (:message_id, :chunk_id, :model_id, :similarity_score, :rank)
                    """
                ),
                {
                    "message_id": asst_msg_id,
                    "chunk_id": chunk["chunk_id"],
                    "model_id": embedding_model_id,
                    "similarity_score": chunk["similarity_score"],
                    "rank": chunk["rank"],
                },
            )
            citations_data.append({
                "chunk_id": str(chunk["chunk_id"]),
                "similarity_score": chunk["similarity_score"],
                "rank": chunk["rank"],
            })

    # 8. Auto-generate title on first exchange completion (2 messages total)
    count_res = await session.execute(
        text("SELECT COUNT(*) AS cnt FROM messages WHERE conversation_id = :conversation_id"),
        {"conversation_id": conversation_id},
    )
    msg_count = count_res.mappings().one()["cnt"]
    if msg_count == 2:
        new_title = generate_conversation_title(user_content, assistant_reply)
        await session.execute(
            text("UPDATE conversations SET title = :title, updated_at = now() WHERE id = :conversation_id"),
            {"title": new_title, "conversation_id": conversation_id},
        )

    await session.commit()

    # 9. Yield the final payload detailing the created message and citations
    final_payload = {
        "message_id": str(asst_msg_id),
        "citations": citations_data,
    }
    yield f"data: {json.dumps(final_payload)}\n\n"


@router.post("", response_model=None)
async def create_message(
    conversation_id: UUID,
    payload: MessageCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    """
    Main endpoint for sending user messages. Saves user query immediately,
    and returns a StreamingResponse using Server-Sent Events (SSE).
    """
    # Verify conversation ownership and save the user message synchronously
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
                INSERT INTO messages (conversation_id, parent_message_id, role, content)
                VALUES (:conversation_id, :parent_message_id, 'user', :content)
                RETURNING id
                """
            ),
            {
                "conversation_id": conversation_id,
                "parent_message_id": payload.parent_message_id,
                "content": payload.content,
            },
        )
        user_msg_id = user_msg_res.mappings().one()["id"]
        await session.commit()

    # Run the streaming RAG-LLM pipeline using a dedicated session context inside the generator
    async def sse_generator():
        async with AsyncSessionLocal() as session:
            async for chunk in stream_rag_llm_response(
                session=session,
                conversation_id=conversation_id,
                user_message_id=user_msg_id,
                parent_message_id=payload.parent_message_id,
                user_id=user_id,
            ):
                yield chunk

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.get("", response_model=list[MessageRead])
async def list_messages(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> list[MessageRead]:
    # Check conversation ownership
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
    """
    Regenerates an assistant response, allowing edited content for user messages.
    Supports chat branching via parent_message_id links.
    """
    async with AsyncSessionLocal() as session:
        # Query target message details
        msg_res = await session.execute(
            text(
                """
                SELECT m.id, m.conversation_id, m.role, m.parent_message_id, m.content, c.user_id
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE m.id = :id
                """
            ),
            {"id": message_id},
        )
        msg_row = msg_res.mappings().one_or_none()
        if msg_row is None or str(msg_row["user_id"]) != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

        conversation_id = msg_row["conversation_id"]

        if msg_row["role"] == "assistant":
            # Regenerate the reply for the user query that prompted this assistant message
            user_message_id = msg_row["parent_message_id"]
            if user_message_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot regenerate assistant response with no parent user query."
                )
                
            if payload.content is not None:
                # User edited the query text: branch new user message
                new_user_msg = await session.execute(
                    text(
                        """
                        INSERT INTO messages (conversation_id, parent_message_id, role, content)
                        VALUES (:conversation_id, :parent_message_id, 'user', :content)
                        RETURNING id
                        """
                    ),
                    {
                        "conversation_id": conversation_id,
                        "parent_message_id": user_message_id,
                        "content": payload.content,
                    },
                )
                active_user_msg_id = new_user_msg.mappings().one()["id"]
                branch_parent_id = message_id  # branch from the old assistant reply
            else:
                active_user_msg_id = user_message_id
                branch_parent_id = message_id
            await session.commit()
        else:
            # Target is a user message
            if payload.content is not None:
                # User edits content: branch new user message from it
                new_user_msg = await session.execute(
                    text(
                        """
                        INSERT INTO messages (conversation_id, parent_message_id, role, content)
                        VALUES (:conversation_id, :parent_message_id, 'user', :content)
                        RETURNING id
                        """
                    ),
                    {
                        "conversation_id": conversation_id,
                        "parent_message_id": message_id,
                        "content": payload.content,
                    },
                )
                active_user_msg_id = new_user_msg.mappings().one()["id"]
                branch_parent_id = message_id
            else:
                active_user_msg_id = message_id
                branch_parent_id = message_id
            await session.commit()

    # Stream the reply branching from branch_parent_id
    async def sse_generator():
        async with AsyncSessionLocal() as session:
            async for chunk in stream_rag_llm_response(
                session=session,
                conversation_id=conversation_id,
                user_message_id=active_user_msg_id,
                parent_message_id=branch_parent_id,
                user_id=user_id,
            ):
                yield chunk

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@messages_action_router.post("/{message_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def update_feedback(
    message_id: UUID,
    payload: MessageFeedbackRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> Response:
    # 1. Ownership check
    msg_res = await session.execute(
        text(
            """
            SELECT m.id, c.user_id
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE m.id = :id
            """
        ),
        {"id": message_id},
    )
    msg_row = msg_res.mappings().one_or_none()
    if msg_row is None or str(msg_row["user_id"]) != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

    # 2. Update rating and feedback
    await session.execute(
        text(
            """
            UPDATE messages
            SET is_helpful = :is_helpful,
                feedback_text = :feedback_text
            WHERE id = :message_id
            """
        ),
        {
            "message_id": message_id,
            "is_helpful": payload.is_helpful,
            "feedback_text": payload.feedback_text,
        },
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
