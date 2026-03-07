from openai import OpenAI
from app.config import settings

client = OpenAI(
    base_url=settings.LLM_API_BASE,
    api_key=settings.LLM_API_KEY,
)


def chat_completion(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    stream: bool = False,
):
    """Unified LLM call — works with both OpenAI and GPT-OSS."""
    return client.chat.completions.create(
        model=model or settings.LLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
    )
