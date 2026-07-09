from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
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


async def process_document_background(document_id: UUID, file_path: str, mime_type: str):
    """
    Asynchronous document parsing pipeline. Extracts text, chunks it,
    generates 1536-dimensional embeddings, and saves chunks and embeddings to the DB.
    """
    async with AsyncSessionLocal() as session:
        try:
            # 1. Update status to processing
            await session.execute(
                text("UPDATE documents SET status = 'processing' WHERE id = :id"),
                {"id": document_id},
            )
            await session.commit()

            # 2. Extract text from the physical file
            text_content = extract_text(file_path, mime_type)
            
            # 3. Split the text content into sliding-window overlap chunks
            chunks = chunk_text(text_content)

            # 4. Fetch the first available embedding model registration
            em_res = await session.execute(
                text("SELECT id FROM embedding_models ORDER BY created_at ASC LIMIT 1")
            )
            em_row = em_res.mappings().one_or_none()

            if em_row and chunks:
                model_id = em_row["id"]
                for chunk in chunks:
                    # A. Insert text chunk
                    chunk_res = await session.execute(
                        text(
                            """
                            INSERT INTO document_chunks (document_id, chunk_number, page_number, chunk_text, token_count)
                            VALUES (:document_id, :chunk_number, :page_number, :chunk_text, :token_count)
                            RETURNING id
                            """
                        ),
                        {
                            "document_id": document_id,
                            "chunk_number": chunk["chunk_number"],
                            "page_number": chunk["page_number"],
                            "chunk_text": chunk["chunk_text"],
                            "token_count": max(1, len(chunk["chunk_text"]) // 4),
                        },
                    )
                    chunk_id = chunk_res.mappings().one()["id"]

                    # B. Generate vector embedding
                    embedding_vector = get_embedding(chunk["chunk_text"])

                    # C. Save embedding in database
                    await session.execute(
                        text(
                            """
                            INSERT INTO chunk_embeddings (chunk_id, embedding_model_id, embedding)
                            VALUES (:chunk_id, :model_id, :embedding)
                            """
                        ),
                        {
                            "chunk_id": chunk_id,
                            "model_id": model_id,
                            "embedding": embedding_vector,
                        },
                    )

            # 5. Set document status to ready
            await session.execute(
                text("UPDATE documents SET status = 'ready' WHERE id = :id"),
                {"id": document_id},
            )
            await session.commit()

        except Exception as exc:
            # Mark document as failed
            print(f"[Ingestion Error] Failed to process document {document_id}: {exc}")
            await session.execute(
                text("UPDATE documents SET status = 'failed' WHERE id = :id"),
                {"id": document_id},
            )
            await session.commit()


@router.post("", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    conversation_id: UUID | None = Form(default=None),
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> Response:
    # 1. Enforce max file size check (read headers or seek)
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 50MB limit."
        )

    # 2. Sniff actual file byte signature to identify MIME type
    sniff_bytes = await file.read(2048)
    await file.seek(0)
    
    detected_mime = None
    for signature, mime in ALLOWED_MIME_SIGNATURES.items():
        if sniff_bytes.startswith(signature):
            detected_mime = mime
            break
            
    if detected_mime is None:
        # Default fallback: check client-supplied type or treat as text if safe
        if file.content_type in ["text/plain", "application/json", "text/markdown"]:
            detected_mime = file.content_type
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported file format. Only PDF, DOCX, PNG, JPEG, and plain text files are allowed."
            )

    # 3. Calculate SHA-256 hash of file content to check for deduplication
    file_content = await file.read()
    await file.seek(0)
    content_hash = hashlib.sha256(file_content).hexdigest()

    # 4. Query global deduplication index
    existing_doc_res = await session.execute(
        text(
            """
            SELECT id, name, description, storage_path, content_hash, mime_type, file_size, status, uploaded_at
            FROM documents
            WHERE content_hash = :content_hash
            """
        ),
        {"content_hash": content_hash},
    )
    existing_doc = existing_doc_res.mappings().one_or_none()

    if existing_doc is not None:
        doc_id = existing_doc["id"]
        
        # A. Link user to the global document (idempotent mapping)
        await session.execute(
            text(
                """
                INSERT INTO user_documents (user_id, document_id)
                VALUES (:user_id, :document_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"user_id": user_id, "document_id": doc_id},
        )
        
        # B. Link conversation to the global document (idempotent mapping)
        if conversation_id:
            # Verify conversation ownership
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
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"conversation_id": conversation_id, "document_id": doc_id},
            )
            
        await session.commit()
        
        # Return ready immediately on deduplication reuse
        return Response(
            content=json.dumps(
                {
                    "id": str(doc_id),
                    "name": existing_doc["name"],
                    "description": existing_doc["description"],
                    "storage_path": existing_doc["storage_path"],
                    "content_hash": existing_doc["content_hash"],
                    "mime_type": existing_doc["mime_type"],
                    "file_size": existing_doc["file_size"],
                    "status": "ready",
                    "uploaded_at": existing_doc["uploaded_at"].isoformat()
                }
            ),
            media_type="application/json",
            status_code=status.HTTP_200_OK,
        )

    # 5. New upload: Save physical file to disk
    os.makedirs("tmp/uploads", exist_ok=True)
    temp_id = hashlib.md5(f"{content_hash}_{datetime.now(timezone.utc).timestamp()}".encode()).hexdigest()
    storage_path = f"tmp/uploads/{temp_id}.bin"
    
    with open(storage_path, "wb") as f:
        f.write(file_content)

    # 6. Insert new document record
    new_doc_res = await session.execute(
        text(
            """
            INSERT INTO documents (name, storage_path, content_hash, mime_type, file_size, status)
            VALUES (:name, :storage_path, :content_hash, :mime_type, :file_size, 'uploading')
            RETURNING id, name, description, storage_path, content_hash, mime_type, file_size, status, uploaded_at
            """
        ),
        {
            "name": file.filename or "uploaded_file",
            "storage_path": storage_path,
            "content_hash": content_hash,
            "mime_type": detected_mime,
            "file_size": file_size,
        },
    )
    doc_row = new_doc_res.mappings().one()
    doc_id = doc_row["id"]

    # 7. Create ownership and conversation scopes
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

    # 8. Dispatch parsing workflow to background tasks
    background_tasks.add_task(
        process_document_background,
        document_id=doc_id,
        file_path=storage_path,
        mime_type=detected_mime,
    )

    return Response(
        content=json.dumps(
            {
                "id": str(doc_id),
                "name": doc_row["name"],
                "description": doc_row["description"],
                "storage_path": doc_row["storage_path"],
                "content_hash": doc_row["content_hash"],
                "mime_type": doc_row["mime_type"],
                "file_size": doc_row["file_size"],
                "status": "uploading",
                "uploaded_at": doc_row["uploaded_at"].isoformat()
            }
        ),
        media_type="application/json",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, str]:
    # Ensure document is owned by this user
    chk = await session.execute(
        text("SELECT document_id FROM user_documents WHERE user_id = :user_id AND document_id = :doc_id"),
        {"user_id": user_id, "doc_id": document_id},
    )
    if chk.mappings().one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    res = await session.execute(
        text("SELECT status FROM documents WHERE id = :id"),
        {"id": document_id},
    )
    row = res.mappings().one_or_none()
    return {"status": row["status"] if row else "unknown"}


@router.delete("/conversations/{conversation_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_document(
    conversation_id: UUID,
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> Response:
    # 1. Verify conversation ownership
    conv = await session.execute(
        text("SELECT id FROM conversations WHERE id = :id AND user_id = :user_id"),
        {"id": conversation_id, "user_id": user_id},
    )
    if conv.mappings().one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    # 2. Delete scoping record
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

    # 3. Periodic style cleanup: Check if the document is still referenced in either user_documents or conversation_documents
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
        # Delete file from disk and remove from documents globally
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
