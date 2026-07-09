import asyncio
from collections.abc import AsyncIterator
import json
from typing import List

import httpx

from app.config import get_settings


def _build_prompt(
    system_prompt: str | None,
    history: List[dict],
    retrieved_chunks: List[dict],
) -> str:
    prompt_parts: List[str] = []

    if system_prompt:
        prompt_parts.append(f"System: {system_prompt}")

    if retrieved_chunks:
        prompt_parts.append("Context:")
        for chunk in retrieved_chunks:
            prompt_parts.append(
                f"- [Page {chunk.get('page_number')} Rank {chunk.get('rank')}]: {chunk.get('chunk_text')}"
            )

    if history:
        prompt_parts.append("Conversation:")
        for message in history:
            role = message.get("role", "user").capitalize()
            prompt_parts.append(f"{role}: {message.get('content', '')}")

    prompt_parts.append("Assistant:")
    prompt_parts.append(
        "Please answer the user's query using the context and conversation above. "
        "If the answer cannot be derived from context, answer using general knowledge."
    )

    return "\n".join(prompt_parts).strip()


async def stream_model_response(
    system_prompt: str | None,
    history: List[dict],
    retrieved_chunks: List[dict],
    model_name: str,
    generation_config: dict,
) -> AsyncIterator[str]:
    """
    Calls the Hugging Face Inference API and streams the generated text as SSE tokens.
    """
    settings = get_settings()
    api_token = settings.huggingface_api_token
    if not api_token:
        raise RuntimeError(
            "Hugging Face API token is not configured. Set HUGGINGFACE_API_TOKEN in the environment."
        )

    prompt = _build_prompt(system_prompt, history, retrieved_chunks)
    url = f"{settings.huggingface_api_url.rstrip('/')}/{model_name}"
    payload = {
        "inputs": prompt,
        "parameters": generation_config or {},
        "options": {"wait_for_model": True},
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    if isinstance(data, list) and data:
        generated_text = data[0].get("generated_text") or data[0].get("text") or str(data[0])
    elif isinstance(data, dict):
        generated_text = data.get("generated_text") or data.get("text") or json.dumps(data)
    else:
        generated_text = str(data)

    words = generated_text.split(" ")
    for i, word in enumerate(words):
        space = " " if i < len(words) - 1 else ""
        token_payload = {"token": word + space}
        yield f"data: {json.dumps(token_payload)}\n\n"
        await asyncio.sleep(0.01)


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