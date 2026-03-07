from loguru import logger

from app.llm_client import chat_completion
from app.core.prompts import SYSTEM_CODEGEN


class CodegenService:
    def __init__(self):
        # In-memory template store (swap for DB in production)
        self._templates: dict[str, dict] = {}

    async def generate(
        self,
        prompt: str,
        project_id: str | None = None,
        language: str = "python",
        framework: str | None = None,
    ) -> dict:
        """Generate code based on prompt and project context."""
        # Build project context
        project_context = ""
        if project_id and project_id in self._templates:
            tmpl = self._templates[project_id]
            project_context = (
                f"Tech stack: {tmpl['tech_stack']}\n"
                f"Conventions: {tmpl.get('conventions', 'N/A')}\n"
                f"Sample code:\n{tmpl.get('sample_code', 'N/A')}"
            )

        system_prompt = SYSTEM_CODEGEN.format(
            language=language,
            framework=framework or "none",
        )

        user_content = prompt
        if project_context:
            user_content = f"Project context:\n{project_context}\n\nRequest: {prompt}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        response = chat_completion(messages=messages, temperature=0.3)
        code = response.choices[0].message.content

        logger.info(f"Codegen [{language}]: {prompt[:50]}...")
        return {
            "code": code,
            "language": language,
            "explanation": f"Generated {language} code for: {prompt[:100]}",
        }

    async def register_template(
        self,
        project_id: str,
        tech_stack: str,
        conventions: str = "",
        sample_code: str = "",
    ) -> dict:
        self._templates[project_id] = {
            "project_id": project_id,
            "tech_stack": tech_stack,
            "conventions": conventions,
            "sample_code": sample_code,
        }
        logger.info(f"Registered template: {project_id}")
        return {"status": "registered", "project_id": project_id}

    async def list_templates(self) -> list[dict]:
        return [
            {"project_id": k, "tech_stack": v["tech_stack"]}
            for k, v in self._templates.items()
        ]
