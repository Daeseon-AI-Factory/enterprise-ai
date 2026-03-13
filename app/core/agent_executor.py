"""Agent Executor — ReAct loop engine for autonomous AI agents.

Implements the Think → Act → Observe loop pattern.
Uses text parsing (not native function calling) for maximum LLM compatibility.
"""

from __future__ import annotations

import json
import re
import asyncio
from dataclasses import dataclass, field
from typing import AsyncGenerator

from loguru import logger

from app.core.tool_registry import ToolRegistry, parse_tool_arguments
from app.llm_client import chat_completion


@dataclass
class AgentStep:
    """A single step in the agent execution trace."""
    step_number: int
    thought: str = ""
    action: str = ""
    action_input: str = ""
    observation: str = ""
    is_final: bool = False
    final_answer: str = ""


@dataclass
class AgentResult:
    """Complete result of an agent execution."""
    task: str
    answer: str
    steps: list[AgentStep] = field(default_factory=list)
    total_iterations: int = 0
    status: str = "completed"  # completed, max_iterations, error


REACT_SYSTEM_PROMPT = """You are an AI agent that can use tools to accomplish tasks.
You must follow the ReAct pattern strictly.

{tool_descriptions}

## Response Format

For each step, respond in EXACTLY this format:

Thought: [your reasoning about what to do next]
Action: [tool name to use]
Action Input: [JSON arguments for the tool]

After receiving the observation, continue with another Thought/Action/Action Input cycle.

When you have enough information to answer, respond with:

Thought: [your final reasoning]
Final Answer: [your complete answer to the user's task]

## Rules
- Use EXACTLY ONE action per response
- Action must be one of the available tool names
- Action Input must be valid JSON
- Always think before acting
- If a tool returns an error, try a different approach
- Use the same language as the user's task
- Be thorough but efficient — don't use tools unnecessarily
"""


class AgentExecutor:
    """Executes a ReAct agent loop with the given tool registry."""

    def __init__(
        self,
        registry: ToolRegistry,
        max_iterations: int = 10,
        tool_timeout: float = 30.0,
    ):
        self.registry = registry
        self.max_iterations = max_iterations
        self.tool_timeout = tool_timeout

    async def run(self, task: str, tools: list[str] | None = None) -> AgentResult:
        """Run the agent to completion and return the full result."""
        steps = []
        answer = ""
        status = "completed"

        async for step in self.run_stream(task, tools):
            steps.append(step)
            if step.is_final:
                answer = step.final_answer

        if not answer and steps:
            status = "max_iterations"
            answer = "에이전트가 최대 반복 횟수에 도달했습니다. 마지막 관찰 결과를 확인하세요."

        return AgentResult(
            task=task,
            answer=answer,
            steps=steps,
            total_iterations=len(steps),
            status=status,
        )

    async def run_stream(
        self, task: str, tools: list[str] | None = None
    ) -> AsyncGenerator[AgentStep, None]:
        """Run the agent and yield each step for streaming."""
        tool_block = self.registry.to_prompt_block(tools)
        system_prompt = REACT_SYSTEM_PROMPT.format(tool_descriptions=tool_block)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {task}"},
        ]

        for i in range(1, self.max_iterations + 1):
            # Call LLM
            try:
                response = chat_completion(
                    messages=messages,
                    temperature=0.1,
                    max_tokens=2048,
                )
                llm_output = response.choices[0].message.content
            except Exception as e:
                logger.error(f"Agent LLM call failed at step {i}: {e}")
                step = AgentStep(step_number=i, thought=f"LLM 호출 실패: {e}", is_final=True, final_answer=str(e))
                yield step
                return

            # Parse the response
            step = self._parse_response(llm_output, i)

            if step.is_final:
                yield step
                return

            # Execute the tool
            if step.action:
                logger.info(f"Agent step {i}: {step.action}({step.action_input})")
                try:
                    args = parse_tool_arguments(step.action_input)
                    observation = await asyncio.wait_for(
                        self.registry.execute(step.action, args),
                        timeout=self.tool_timeout,
                    )
                except asyncio.TimeoutError:
                    observation = f"Error: Tool '{step.action}' timed out after {self.tool_timeout}s"
                except Exception as e:
                    observation = f"Error: {str(e)}"

                step.observation = observation
            else:
                step.observation = "No action was taken. Please specify an action or provide a Final Answer."

            yield step

            # Add to conversation for next iteration
            messages.append({"role": "assistant", "content": llm_output})
            messages.append({"role": "user", "content": f"Observation: {step.observation}"})

        # Max iterations reached
        step = AgentStep(
            step_number=self.max_iterations + 1,
            thought="최대 반복 횟수에 도달했습니다.",
            is_final=True,
            final_answer="최대 반복 횟수에 도달하여 작업을 중단합니다. 수집된 정보를 바탕으로 부분적인 답변을 제공합니다.",
        )
        yield step

    @staticmethod
    def _parse_response(text: str, step_number: int) -> AgentStep:
        """Parse LLM output into a structured AgentStep."""
        step = AgentStep(step_number=step_number)

        # Check for Final Answer
        final_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL)
        if final_match:
            step.is_final = True
            step.final_answer = final_match.group(1).strip()
            # Extract thought before final answer
            thought_match = re.search(r"Thought:\s*(.*?)(?=Final Answer:)", text, re.DOTALL)
            if thought_match:
                step.thought = thought_match.group(1).strip()
            return step

        # Extract Thought
        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|$)", text, re.DOTALL)
        if thought_match:
            step.thought = thought_match.group(1).strip()

        # Extract Action
        action_match = re.search(r"Action:\s*(\S+)", text)
        if action_match:
            step.action = action_match.group(1).strip()

        # Extract Action Input
        input_match = re.search(r"Action Input:\s*(.*?)(?=\n\n|Thought:|$)", text, re.DOTALL)
        if input_match:
            step.action_input = input_match.group(1).strip()

        # If no structured output found, treat entire text as thought
        if not step.thought and not step.action:
            step.thought = text.strip()
            # Check if it looks like a final answer without the prefix
            if not any(keyword in text.lower() for keyword in ["search", "query", "look", "check", "find"]):
                step.is_final = True
                step.final_answer = text.strip()

        return step
