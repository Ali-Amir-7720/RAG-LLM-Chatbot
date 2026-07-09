import os
from typing import Any, Dict, List


def extract_text(file_path: str, mime_type: str) -> str:
    """
    Extracts plain text from a file based on its MIME type.
    Supports PDF (via pypdf), DOCX (via python-docx), and plain text.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at {file_path}")

    # Plain text files
    if mime_type.startswith("text/") or mime_type in ["application/x-javascript", "application/json"]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as exc:
            raise ValueError(f"Failed to read plain text file: {exc}") from exc

    # PDF documents
    elif mime_type == "application/pdf":
        try:
            import pypdf
            text_content = []
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
            return "\n\n".join(text_content)
        except ImportError:
            # Fallback if library not installed yet
            return f"[PDF Parsing Fallback: pypdf not installed. File path: {os.path.basename(file_path)}]"
        except Exception as exc:
            raise ValueError(f"Failed to parse PDF document: {exc}") from exc

    # DOCX documents
    elif mime_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
    ]:
        try:
            import docx
            doc = docx.Document(file_path)
            text_content = [p.text for p in doc.paragraphs if p.text]
            return "\n".join(text_content)
        except ImportError:
            # Fallback if library not installed yet
            return f"[DOCX Parsing Fallback: python-docx not installed. File path: {os.path.basename(file_path)}]"
        except Exception as exc:
            raise ValueError(f"Failed to parse Word document: {exc}") from exc

    # Other files (images, audio, video) - return placeholder or empty
    else:
        return f"[Media Content Placeholder: {os.path.basename(file_path)}]"


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict[str, Any]]:
    """
    Splits text into chunks using a sliding window character overlap strategy.
    Returns a list of dictionaries with chunk metadata (chunk_number, chunk_text, page_number).
    """
    if not text.strip():
        return []

    chunks = []
    start = 0
    chunk_number = 1

    while start < len(text):
        end = start + chunk_size
        chunk_slice = text[start:end]
        
        # Avoid orphan letters at the end
        if len(chunk_slice) < 50 and chunks:
            break
            
        chunks.append({
            "chunk_number": chunk_number,
            "chunk_text": chunk_slice,
            "page_number": 1,  # Simplified for general text; can be extended for page-specific tagging
        })
        
        chunk_number += 1
        start += (chunk_size - chunk_overlap)

    return chunks
