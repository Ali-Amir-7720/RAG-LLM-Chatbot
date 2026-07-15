from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal, get_db_session
from app.dependencies import get_current_user_id
from app.schemas import DocumentRead
from app.services.embeddings import get_embedding
from app.services.parser import chunk_text, extract_text


router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_SIGNATURES = {
    b"%PDF-": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
}


async def process_document_background(document_id: UUID, file_path: str, mime_type: str) -> None:
    async with AsyncSessionLocal() as session:
        try:
            text_content = extract_text(file_path, mime_type)
            chunks = chunk_text(text_content)

            for chunk in chunks:
                chunk_res = await session.execute(
                    text(
                        """
                        INSERT INTO document_chunks (document_id, chunk_number, chunk_text)
                        VALUES (:document_id, :chunk_number, :chunk_text)
                        RETURNING id
                        """
                    ),
                    {
                        "document_id": document_id,
                        "chunk_number": chunk["chunk_number"],
                        "chunk_text": chunk["chunk_text"],
                    },
                )
                chunk_id = chunk_res.mappings().one()["id"]

                try:
                    embedding = get_embedding(chunk["chunk_text"])
                    await session.execute(
                        text(
                            """
                            INSERT INTO chunk_embeddings (chunk_id, embedding)
                            VALUES (:chunk_id, :embedding)
                            """
                        ),
                        {"chunk_id": chunk_id, "embedding": embedding},
                    )
                except Exception:
                    # Embedding provider may be unavailable; keep text chunks anyway.
                    continue

            await session.commit()
        except Exception:
            await session.rollback()


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
    file: UploadFile = File(...),
    conversation_id: UUID | None = Form(default=None),
) -> DocumentRead:
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 50MB limit.",
        )

    sniff_bytes = file_content[:2048]
    detected_mime = None
    for signature, mime in ALLOWED_MIME_SIGNATURES.items():
        if sniff_bytes.startswith(signature):
            detected_mime = mime
            break

    if detected_mime is None:
        if file.content_type in ["text/plain", "application/json", "text/markdown"]:
            detected_mime = file.content_type
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported file format. Only PDF, DOCX, PNG, JPEG, and plain text files are allowed.",
            )

    os.makedirs("tmp/uploads", exist_ok=True)
    temp_id = hashlib.md5(
        f"{user_id}_{file.filename}_{datetime.now(timezone.utc).timestamp()}".encode()
    ).hexdigest()
    storage_path = f"tmp/uploads/{temp_id}.bin"
    with open(storage_path, "wb") as handle:
        handle.write(file_content)

    new_doc_res = await session.execute(
        text(
            """
            INSERT INTO documents (name, storage_path, mime_type, file_size)
            VALUES (:name, :storage_path, :mime_type, :file_size)
            RETURNING id, name, storage_path, mime_type, file_size, created_at
            """
        ),
        {
            "name": file.filename or "uploaded_file",
            "storage_path": storage_path,
            "mime_type": detected_mime,
            "file_size": file_size,
        },
    )
    doc_row = new_doc_res.mappings().one()
    doc_id = doc_row["id"]

    await session.execute(
        text(
            """
            INSERT INTO user_documents (user_id, document_id)
            VALUES (:user_id, :document_id)
            """
        ),
        {"user_id": user_id, "document_id": doc_id},
    )

    if conversation_id:
        conv = await session.execute(
            text("SELECT id FROM conversations WHERE id = :id AND user_id = :user_id"),
            {"id": conversation_id, "user_id": user_id},
        )
        if conv.mappings().one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

        await session.execute(
            text(
                """
                INSERT INTO conversation_documents (conversation_id, document_id)
                VALUES (:conversation_id, :document_id)
                """
            ),
            {"conversation_id": conversation_id, "document_id": doc_id},
        )

    await session.commit()

    background_tasks.add_task(
        process_document_background,
        document_id=doc_id,
        file_path=storage_path,
        mime_type=detected_mime,
    )

    return DocumentRead.model_validate(doc_row)


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, str]:
    chk = await session.execute(
        text(
            """
            SELECT document_id
            FROM user_documents
            WHERE user_id = :user_id AND document_id = :doc_id
            """
        ),
        {"user_id": user_id, "doc_id": document_id},
    )
    if chk.mappings().one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    chunk_res = await session.execute(
        text("SELECT COUNT(*) AS cnt FROM document_chunks WHERE document_id = :id"),
        {"id": document_id},
    )
    count = int(chunk_res.mappings().one()["cnt"])
    return {"status": "ready" if count > 0 else "processing"}


@router.delete(
    "/conversations/{conversation_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation_document(
    conversation_id: UUID,
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> Response:
    conv = await session.execute(
        text("SELECT id FROM conversations WHERE id = :id AND user_id = :user_id"),
        {"id": conversation_id, "user_id": user_id},
    )
    if conv.mappings().one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    del_res = await session.execute(
        text(
            """
            DELETE FROM conversation_documents
            WHERE conversation_id = :conversation_id AND document_id = :document_id
            RETURNING document_id
            """
        ),
        {"conversation_id": conversation_id, "document_id": document_id},
    )
    if del_res.mappings().one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document scope not found.")

    ref_check = await session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1 FROM user_documents WHERE document_id = :document_id
                UNION ALL
                SELECT 1 FROM conversation_documents WHERE document_id = :document_id
            ) AS has_ref
            """
        ),
        {"document_id": document_id},
    )
    has_ref = ref_check.mappings().one()["has_ref"]

    if not has_ref:
        path_res = await session.execute(
            text("SELECT storage_path FROM documents WHERE id = :id"),
            {"id": document_id},
        )
        path_row = path_res.mappings().one_or_none()
        if path_row and os.path.exists(path_row["storage_path"]):
            try:
                os.remove(path_row["storage_path"])
            except Exception:
                pass

        await session.execute(
            text("DELETE FROM documents WHERE id = :id"),
            {"id": document_id},
        )

    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
