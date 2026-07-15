from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.dependencies import get_current_user_id
from app.schemas import ConversationCreateRequest, ConversationRead, SearchResult


router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> ConversationRead:
    title = payload.title.strip() if payload.title else None
    if not title:
        title = "New conversation"

    result = await session.execute(
        text(
            """
            INSERT INTO conversations (
                user_id, title, model_name, system_prompt, generation_config
            )
            VALUES (
                :user_id, :title, :model_name, :system_prompt, CAST(:generation_config AS jsonb)
            )
            RETURNING
                id, user_id, title, model_name, system_prompt, generation_config,
                is_archived, created_at, updated_at
            """
        ),
        {
            "user_id": user_id,
            "title": title,
            "model_name": payload.model_name or "default",
            "system_prompt": payload.system_prompt,
            "generation_config": json.dumps(payload.generation_config or {}),
        },
    )
    await session.commit()
    return ConversationRead.model_validate(result.mappings().one())


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
    archived: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ConversationRead]:
    result = await session.execute(
        text(
            """
            SELECT
                id, user_id, title, model_name, system_prompt, generation_config,
                is_archived, created_at, updated_at
            FROM conversations
            WHERE user_id = :user_id
              AND is_archived = :archived
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"user_id": user_id, "archived": archived, "limit": limit, "offset": offset},
    )
    return [ConversationRead.model_validate(row) for row in result.mappings().all()]


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def update_conversation(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
    title: str | None = None,
    is_archived: bool | None = None,
) -> ConversationRead:
    result = await session.execute(
        text(
            """
            SELECT
                id, user_id, title, model_name, system_prompt, generation_config,
                is_archived, created_at, updated_at
            FROM conversations
            WHERE id = :id AND user_id = :user_id
            """
        ),
        {"id": conversation_id, "user_id": user_id},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    new_title = row["title"]
    if title is not None:
        cleaned = title.strip()
        if not cleaned:
            raise HTTPException(status_code=400, detail="title cannot be empty")
        new_title = cleaned

    new_archived = row["is_archived"] if is_archived is None else is_archived

    updated = await session.execute(
        text(
            """
            UPDATE conversations
            SET title = :title,
                is_archived = :is_archived,
                updated_at = now()
            WHERE id = :id AND user_id = :user_id
            RETURNING
                id, user_id, title, model_name, system_prompt, generation_config,
                is_archived, created_at, updated_at
            """
        ),
        {
            "id": conversation_id,
            "user_id": user_id,
            "title": new_title,
            "is_archived": new_archived,
        },
    )
    await session.commit()
    return ConversationRead.model_validate(updated.mappings().one())


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> Response:
    result = await session.execute(
        text(
            """
            DELETE FROM conversations
            WHERE id = :id AND user_id = :user_id
            RETURNING id
            """
        ),
        {"id": conversation_id, "user_id": user_id},
    )
    await session.commit()
    if result.mappings().one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/search", response_model=list[SearchResult])
async def search_conversations(
    q: str = Query(min_length=1),
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> list[SearchResult]:
    result = await session.execute(
        text(
            """
            SELECT m.id AS message_id,
                   m.conversation_id,
                   LEFT(m.content, 200) AS snippet,
                   1.0::float AS rank
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.user_id = :user_id
              AND m.content ILIKE :pattern
            ORDER BY m.created_at DESC
            LIMIT 50
            """
        ),
        {"user_id": user_id, "pattern": f"%{q}%"},
    )
    return [SearchResult.model_validate(row) for row in result.mappings().all()]


@router.get("/{conversation_id}/export")
async def export_conversation(
    conversation_id: UUID,
    format: str = Query(default="markdown"),
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> Response:
    conv = await session.execute(
        text("SELECT id, title FROM conversations WHERE id = :id AND user_id = :user_id"),
        {"id": conversation_id, "user_id": user_id},
    )
    conv_row = conv.mappings().one_or_none()
    if conv_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    messages_result = await session.execute(
        text(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = :conversation_id
            ORDER BY created_at ASC
            """
        ),
        {"conversation_id": conversation_id},
    )
    rows = messages_result.mappings().all()

    if format.lower() == "pdf":
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << >> /Contents 4 0 R >>\nendobj\n"
            b"4 0 obj\n<< /Length 50 >>\nstream\n"
            b"BT /F1 12 Tf 70 700 Td (Conversation Export PDF) Tj ET\n"
            b"endstream\nendobj\nxref\n0 5\n0000000000 65535 f\n"
            b"0000000009 00000 n\n0000000062 00000 n\n0000000121 00000 n\n"
            b"0000000224 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n323\n%%EOF"
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="conversation_{conversation_id}.pdf"'
            },
        )

    md_lines = [f"# {conv_row['title']}\n"]
    for msg in rows:
        role_label = "User" if msg["role"] == "user" else "Assistant"
        md_lines.append(
            f"### {role_label} ({msg['created_at'].strftime('%Y-%m-%d %H:%M:%S')})\n{msg['content']}\n"
        )

    return Response(
        content="\n".join(md_lines),
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="conversation_{conversation_id}.md"'
        },
    )
