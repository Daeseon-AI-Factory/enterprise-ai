"""Tool Registry — defines tools that AI Agent and Function Calling can use.

CORE_CANDIDATE: This module is reusable across products.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from loguru import logger


@dataclass
class Tool:
    """A tool that the AI agent can invoke."""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for parameters
    handler: Callable[..., Awaitable[str]]  # async function that returns string result

    def to_openai_function(self) -> dict:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_prompt_description(self) -> str:
        """Format tool for text-based prompt injection."""
        params_desc = []
        props = self.parameters.get("properties", {})
        required = self.parameters.get("required", [])
        for name, schema in props.items():
            req = " (required)" if name in required else " (optional)"
            params_desc.append(f"    - {name}: {schema.get('description', schema.get('type', 'string'))}{req}")
        params_str = "\n".join(params_desc) if params_desc else "    (no parameters)"
        return f"- **{self.name}**: {self.description}\n  Parameters:\n{params_str}"


class ToolRegistry:
    """Central registry of tools available to agents and function calling."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self, names: list[str] | None = None) -> list[Tool]:
        if names:
            return [self._tools[n] for n in names if n in self._tools]
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def to_openai_tools(self, names: list[str] | None = None) -> list[dict]:
        """Export tools in OpenAI function calling format."""
        return [t.to_openai_function() for t in self.list_tools(names)]

    def to_prompt_block(self, names: list[str] | None = None) -> str:
        """Export tools as text block for prompt-based function calling."""
        tools = self.list_tools(names)
        if not tools:
            return "No tools available."
        lines = ["Available tools:"]
        for tool in tools:
            lines.append(tool.to_prompt_description())
        return "\n\n".join(lines)

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name with given arguments."""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found. Available: {', '.join(self._tools.keys())}"
        try:
            result = await tool.handler(**arguments)
            # Truncate long results to prevent context overflow
            if len(result) > 3000:
                result = result[:3000] + "\n... (truncated)"
            return result
        except Exception as e:
            logger.error(f"Tool '{name}' execution failed: {e}")
            return f"Error executing tool '{name}': {str(e)}"


def parse_tool_arguments(raw: str) -> dict[str, Any]:
    """Parse tool arguments from string (JSON or key=value format)."""
    raw = raw.strip()
    # Try JSON first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try key=value pairs
    args = {}
    for part in raw.split(","):
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            args[key.strip()] = value.strip().strip('"').strip("'")
    return args
