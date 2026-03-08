"""AI-powered code review service — uses internal LLM for analysis."""

from __future__ import annotations

from app.llm_client import chat_completion
from app.core.prompts import SYSTEM_CODE_REVIEW, SYSTEM_EDGE_CASE_REVIEW


class ReviewService:
    async def code_review(
        self,
        code: str,
        language: str = "",
        context: str = "",
    ) -> dict:
        """Perform AI code review on the given code."""
        user_prompt = self._build_review_prompt(code, language, context)
        messages = [
            {"role": "system", "content": SYSTEM_CODE_REVIEW},
            {"role": "user", "content": user_prompt},
        ]
        response = chat_completion(messages=messages, temperature=0.3, max_tokens=4096)
        return {
            "review": response.choices[0].message.content,
            "language": language,
        }

    async def edge_case_review(
        self,
        code: str,
        language: str = "",
        context: str = "",
    ) -> dict:
        """Analyze code for edge cases and boundary conditions."""
        user_prompt = self._build_review_prompt(code, language, context)
        messages = [
            {"role": "system", "content": SYSTEM_EDGE_CASE_REVIEW},
            {"role": "user", "content": user_prompt},
        ]
        response = chat_completion(messages=messages, temperature=0.3, max_tokens=4096)
        return {
            "analysis": response.choices[0].message.content,
            "language": language,
        }

    @staticmethod
    def _build_review_prompt(code: str, language: str, context: str) -> str:
        parts = []
        if language:
            parts.append(f"Language: {language}")
        if context:
            parts.append(f"Context: {context}")
        parts.append(f"```{language}\n{code}\n```")
        return "\n\n".join(parts)
