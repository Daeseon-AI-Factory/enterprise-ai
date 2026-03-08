"""Build & Deploy pipeline service for air-gapped environments.

Runs build/deploy as local subprocess commands. No external CI/CD dependency.
Stores build history in JSON files for persistence.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

from loguru import logger

_BUILD_HISTORY_DIR = "./data/builds"


class BuildService:
    async def run_build(
        self,
        project_path: str,
        build_command: str = "npm run build",
        *,
        name: str = "",
    ) -> dict:
        """Execute a build command and return the result."""
        build_id = str(uuid.uuid4())[:8]
        started_at = datetime.now(timezone.utc).isoformat()

        logger.info(f"[Build {build_id}] Starting: {build_command} in {project_path}")

        # Validate project path exists
        if not os.path.isdir(project_path):
            return self._save_result({
                "build_id": build_id,
                "name": name or build_command,
                "status": "failed",
                "command": build_command,
                "project_path": project_path,
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "stdout": "",
                "stderr": f"Project path does not exist: {project_path}",
                "return_code": 1,
            })

        try:
            proc = await asyncio.create_subprocess_shell(
                build_command,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

            result = {
                "build_id": build_id,
                "name": name or build_command,
                "status": "success" if proc.returncode == 0 else "failed",
                "command": build_command,
                "project_path": project_path,
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "stdout": stdout.decode(errors="replace")[-5000:],  # last 5KB
                "stderr": stderr.decode(errors="replace")[-5000:],
                "return_code": proc.returncode,
            }
        except asyncio.TimeoutError:
            result = {
                "build_id": build_id,
                "name": name or build_command,
                "status": "timeout",
                "command": build_command,
                "project_path": project_path,
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "stdout": "",
                "stderr": "Build timed out after 300 seconds",
                "return_code": -1,
            }
        except Exception as e:
            result = {
                "build_id": build_id,
                "name": name or build_command,
                "status": "error",
                "command": build_command,
                "project_path": project_path,
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
            }

        return self._save_result(result)

    async def run_deploy(
        self,
        project_path: str,
        deploy_command: str,
        *,
        name: str = "",
    ) -> dict:
        """Execute a deploy command. Same mechanics as build."""
        result = await self.run_build(
            project_path=project_path,
            build_command=deploy_command,
            name=name or f"deploy: {deploy_command}",
        )
        result["type"] = "deploy"
        self._save_result(result)
        return result

    async def list_history(self, limit: int = 20) -> list[dict]:
        """Return recent build/deploy history."""
        os.makedirs(_BUILD_HISTORY_DIR, exist_ok=True)
        files = sorted(
            [f for f in os.listdir(_BUILD_HISTORY_DIR) if f.endswith(".json")],
            reverse=True,
        )
        results = []
        for f in files[:limit]:
            path = os.path.join(_BUILD_HISTORY_DIR, f)
            with open(path, "r") as fh:
                data = json.load(fh)
                # Return summary without full logs
                results.append({
                    "build_id": data["build_id"],
                    "name": data.get("name", ""),
                    "status": data["status"],
                    "command": data["command"],
                    "started_at": data["started_at"],
                    "finished_at": data.get("finished_at", ""),
                    "return_code": data.get("return_code", -1),
                })
        return results

    async def get_build_detail(self, build_id: str) -> dict | None:
        """Get full build detail including logs."""
        os.makedirs(_BUILD_HISTORY_DIR, exist_ok=True)
        for f in os.listdir(_BUILD_HISTORY_DIR):
            if build_id in f:
                with open(os.path.join(_BUILD_HISTORY_DIR, f), "r") as fh:
                    return json.load(fh)
        return None

    @staticmethod
    def _save_result(result: dict) -> dict:
        os.makedirs(_BUILD_HISTORY_DIR, exist_ok=True)
        filename = f"{result['started_at'].replace(':', '-')}_{result['build_id']}.json"
        path = os.path.join(_BUILD_HISTORY_DIR, filename)
        with open(path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"[Build {result['build_id']}] {result['status']}")
        return result
