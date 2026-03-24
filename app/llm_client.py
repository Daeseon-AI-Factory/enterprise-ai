import httpx
from openai import OpenAI
from loguru import logger

from app.config import settings

client = OpenAI(
    base_url=settings.LLM_API_BASE,
    api_key=settings.LLM_API_KEY,
    timeout=httpx.Timeout(300.0, connect=10.0),  # 5min timeout for large models
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


def chat_completion_with_tools(
    messages: list[dict],
    tools: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    tool_choice: str = "auto",
):
    """LLM call with function calling / tool use support.

    Falls back to regular chat_completion if the model doesn't support tools.
    """
    try:
        return client.chat.completions.create(
            model=model or settings.LLM_MODEL,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        # If native tool use fails (model doesn't support it), fall back
        logger.warning(f"Native tool calling failed, model may not support it: {e}")
        raise
