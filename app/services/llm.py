import asyncio
from collections.abc import AsyncIterator
import json
import random
from typing import List


async def generate_chat_reply_stream(
    system_prompt: str | None,
    history: List[dict],
    retrieved_chunks: List[dict],
    model_name: str,
) -> AsyncIterator[str]:
    """
    Streams a mock assistant response over SSE (Server-Sent Events) that references
    the retrieved document context chunks to test RAG pipelines and citation tracking.
    Yields data in EventSource format:
      data: {"token": "chunk"}
    """
    # 1. Determine response content based on retrieved chunks
    if retrieved_chunks:
        # Construct a response acknowledging the RAG context
        context_preview = retrieved_chunks[0]["chunk_text"]
        if len(context_preview) > 60:
            context_preview = context_preview[:60] + "..."
            
        sentences = [
            f"Based on the documents attached, specifically regarding: '{context_preview}', ",
            "I found relevant details that clarify your inquiry. ",
            "The retrieved material states that this system integrates FastAPI, pgvector, and Hugging Face models. ",
            "Additionally, document sources show that the database uses a hybrid token authentication model. ",
            "Let me know if you would like me to extract more details from these sources."
        ]
    else:
        sentences = [
            "Hello! I am your AI assistant. ",
            "I can help you analyze documents, answer questions, or write code. ",
            "Currently, there are no documents attached to this conversation. ",
            "Please upload a document (such as a PDF or DOCX) to try out Retrieval-Augmented Generation (RAG)!",
        ]
        
    response_text = "".join(sentences)
    
    # 2. Stream the tokens with simulated latency
    words = response_text.split(" ")
    for i, word in enumerate(words):
        space = " " if i < len(words) - 1 else ""
        token_payload = {"token": word + space}
        yield f"data: {json.dumps(token_payload)}\n\n"
        # Simulate typing latency
        await asyncio.sleep(random.uniform(0.01, 0.05))
        
    # We yield a final yield indicating completion (handled by the caller if needed)


def generate_conversation_title(user_message: str, assistant_message: str) -> str:
    """
    Generates a short, descriptive title based on the first user message.
    """
    words = user_message.strip().split()
    if not words:
        return "New conversation"
        
    title = " ".join(words[:4])
    if len(words) > 4:
        title += "..."
        
    # Clean up trailing punctuation
    title = title.rstrip("?,.!:")
    return title if title else "New conversation"
