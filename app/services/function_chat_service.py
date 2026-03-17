"""Function Calling Chat Service — Smart Chat that auto-uses tools.

Two strategies:
1. Native: Uses OpenAI function calling API (GPT-4, etc.)
2. Prompt: Embeds tools in system prompt, parses XML tags (GPT-OSS fallback)
"""

from __future__ import annotations

import json
import re
import uuid
from typing import AsyncGenerator

from loguru import logger

from app.config import settings
from app.llm_client import chat_completion, chat_completion_with_tools
from app.core.tool_registry import ToolRegistry
from app.core.conversation_store import ConversationStore
from app.core.prompts import SYSTEM_CHAT


FUNCTION_CHAT_SYSTEM = """You are an AI assistant with access to tools.
You can use these tools when the user's question requires searching documents,
querying databases, generating code, or reviewing code.

{tool_descriptions}

## When to use tools
- User asks about specific documents or data → use search_docs
- User asks about database/statistics/numbers → use query_database
- User asks to write code → use generate_code
- User asks to review code → use review_code
- For general conversation, just answer directly without tools

## Tool call format (when you need to use a tool)
To call a tool, include this in your response:
<tool_call>
{{"name": "tool_name", "arguments": {{"param1": "value1"}}}}
</tool_call>

You may call multiple tools. After receiving tool results, provide your final answer.
If you don't need any tools, just respond normally.

Use the same language as the user.
"""


class FunctionChatService:
    def __init__(self, registry: ToolRegistry):
        self._registry = registry
        self._store = ConversationStore()

    async def chat(
        self,
        message: str,
        conversation_id: str | None = None,
        enabled_tools: list[str] | None = None,
    ) -> dict:
        """Smart chat with automatic tool use."""
        conv_id = conversation_id or str(uuid.uuid4())
        history = self._store.load(conv_id)

        try:
            if settings.FUNCTION_CALLING_MODE == "native":
                result = await self._chat_native(message, history, enabled_tools)
            elif settings.FUNCTION_CALLING_MODE == "prompt":
                result = await self._chat_prompt(message, history, enabled_tools)
            else:  # auto
                try:
                    result = await self._chat_native(message, history, enabled_tools)
                except Exception:
                    logger.info("Native function calling failed, falling back to prompt mode")
                    result = await self._chat_prompt(message, history, enabled_tools)
        except Exception as e:
            logger.error(f"Smart chat LLM call failed: {e}")
            return {
                "reply": f"LLM 호출 실패: {e}",
                "conversation_id": conv_id,
                "tools_used": [],
            }

        # Persist conversation
        self._store.append(conv_id, {"role": "user", "content": message})
        self._store.append(conv_id, {"role": "assistant", "content": result["reply"]})

        result["conversation_id"] = conv_id
        return result

    async def chat_stream(
        self,
        message: str,
        conversation_id: str | None = None,
        enabled_tools: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming smart chat — executes tools first, then streams final answer."""
        conv_id = conversation_id or str(uuid.uuid4())

        # Non-streaming tool execution phase
        result = await self.chat(message, conv_id, enabled_tools)

        # Stream the result
        reply = result["reply"]
        chunk_size = 20
        for i in range(0, len(reply), chunk_size):
            chunk = reply[i:i + chunk_size]
            yield f"data: {json.dumps({'content': chunk, 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"

        # Tool usage info
        if result.get("tools_used"):
            yield f"data: {json.dumps({'tools_used': result['tools_used'], 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'done': True, 'conversation_id': conv_id})}\n\n"

    # --- Native Function Calling ---

    async def _chat_native(
        self, message: str, history: list[dict], enabled_tools: list[str] | None
    ) -> dict:
        """Use OpenAI native function calling."""
        messages = [{"role": "system", "content": SYSTEM_CHAT}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        tools_used = []
        openai_tools = self._registry.to_openai_tools(enabled_tools)
        max_rounds = 5  # Prevent infinite tool calling loops

        for _ in range(max_rounds):
            response = chat_completion_with_tools(
                messages=messages,
                tools=openai_tools,
                temperature=0.7,
            )
            choice = response.choices[0]

            if choice.finish_reason == "tool_calls" or (choice.message.tool_calls):
                # Execute tool calls
                messages.append(choice.message)
                for tool_call in choice.message.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)
                    logger.info(f"Function call: {fn_name}({fn_args})")

                    result = await self._registry.execute(fn_name, fn_args)
                    tools_used.append({"tool": fn_name, "args": fn_args})

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
            else:
                # Final response
                return {
                    "reply": choice.message.content,
                    "tools_used": tools_used,
                }

        return {
            "reply": choice.message.content or "도구 호출 한도에 도달했습니다.",
            "tools_used": tools_used,
        }

    # --- Prompt-based Function Calling (Fallback) ---

    async def _chat_prompt(
        self, message: str, history: list[dict], enabled_tools: list[str] | None
    ) -> dict:
        """Use prompt-based tool calling for models without native support."""
        tool_block = self._registry.to_prompt_block(enabled_tools)
        system = FUNCTION_CHAT_SYSTEM.format(tool_descriptions=tool_block)

        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        tools_used = []
        max_rounds = 5

        for _ in range(max_rounds):
            response = chat_completion(messages=messages, temperature=0.7)
            reply = response.choices[0].message.content

            # Parse tool calls from response
            tool_calls = self._parse_tool_calls(reply)

            if not tool_calls:
                # No tool calls — this is the final answer
                # Remove any lingering tool_call tags
                clean_reply = re.sub(r"<tool_call>.*?</tool_call>", "", reply, flags=re.DOTALL).strip()
                return {
                    "reply": clean_reply or reply,
                    "tools_used": tools_used,
                }

            # Execute tool calls and feed results back
            tool_results = []
            for tc in tool_calls:
                logger.info(f"Prompt function call: {tc['name']}({tc['arguments']})")
                result = await self._registry.execute(tc["name"], tc["arguments"])
                tools_used.append({"tool": tc["name"], "args": tc["arguments"]})
                tool_results.append(f"Tool '{tc['name']}' result:\n{result}")

            # Add results to conversation
            messages.append({"role": "assistant", "content": reply})
            messages.append({
                "role": "user",
                "content": "Tool results:\n\n" + "\n\n---\n\n".join(tool_results) + "\n\nPlease provide your final answer based on these results.",
            })

        return {
            "reply": reply,
            "tools_used": tools_used,
        }

    @staticmethod
    def _parse_tool_calls(text: str) -> list[dict]:
        """Extract tool calls from <tool_call> XML tags."""
        calls = []
        pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match)
                if "name" in data:
                    calls.append({
                        "name": data["name"],
                        "arguments": data.get("arguments", {}),
                    })
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool call: {match[:100]}")
        return calls
