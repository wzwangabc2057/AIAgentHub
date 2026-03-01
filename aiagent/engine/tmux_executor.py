"""
tmux executor - core execution engine

Manages Claude CLI execution in tmux sessions with API callback model:
1. Ensure tmux session exists for agent
2. Write prompt to _prompt.txt
3. Send Claude CLI command via tmux send-keys
4. Wait for completion by polling MongoDB (Claude calls done API)
5. Return result from results collection
"""

import asyncio
import os
import time
from typing import Optional
from dataclasses import dataclass
from loguru import logger

from aiagent.config import settings
from aiagent.database import get_db
from aiagent.services.tmux_manager import tmux_manager


@dataclass
class ExecutionResult:
    """Result of an execution"""
    output: str = ""
    status: str = "completed"  # completed, failed, timeout
    error: Optional[str] = None


class TmuxExecutor:
    """tmux container + Claude self-reporting via API callbacks"""

    def __init__(self):
        self.agents_dir = os.path.abspath(settings.agents_dir)

    def _get_work_dir(self, agent_id: str) -> str:
        return os.path.join(self.agents_dir, agent_id)

    def _ensure_session(self, agent_id: str) -> bool:
        """Ensure tmux session exists for this agent"""
        work_dir = self._get_work_dir(agent_id)
        return tmux_manager.create_session(agent_id, work_dir)

    def _write_prompt(self, agent_id: str, prompt: str) -> str:
        """Write prompt to agent's _prompt.txt file"""
        work_dir = self._get_work_dir(agent_id)
        os.makedirs(work_dir, exist_ok=True)
        prompt_path = os.path.join(work_dir, "_prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        return prompt_path

    async def execute(self, execution_id: str, agent_id: str, prompt: str, timeout: int = 300) -> ExecutionResult:
        """
        Execute a prompt in an agent's tmux session.

        1. Ensure tmux session exists
        2. Write prompt file
        3. Send Claude CLI command
        4. Wait for completion (poll MongoDB)
        5. Return result
        """
        # 1. Ensure session
        if not self._ensure_session(agent_id):
            return ExecutionResult(status="failed", error=f"Failed to create tmux session for {agent_id}")

        # 2. Write prompt
        self._write_prompt(agent_id, prompt)
        logger.info(f"[{execution_id}] Prompt written for {agent_id}")

        # 3. Update execution status to running
        db = get_db()
        from datetime import datetime, timezone
        db.executions.update_one(
            {"_id": execution_id},
            {"$set": {"status": "running", "started_at": datetime.now(timezone.utc)}}
        )

        # 4. Send Claude command
        # Use --dangerously-skip-permissions for unattended execution
        command = 'claude --dangerously-skip-permissions "$(cat _prompt.txt)"'
        if not tmux_manager.send_keys(agent_id, command):
            return ExecutionResult(status="failed", error=f"Failed to send command to tmux session {agent_id}")

        logger.info(f"[{execution_id}] Claude started in aah_{agent_id}")

        # 5. Wait for completion
        result = await self._wait_for_completion(execution_id, timeout)
        return result

    async def _wait_for_completion(self, execution_id: str, timeout: int) -> ExecutionResult:
        """Poll MongoDB waiting for Claude to call done API"""
        db = get_db()
        start = time.time()
        poll_interval = settings.poll_interval

        while time.time() - start < timeout:
            execution = db.executions.find_one({"_id": execution_id})
            if not execution:
                return ExecutionResult(status="failed", error="Execution record not found")

            if execution["status"] in ("completed", "failed"):
                # Claude has reported completion via API
                result = db.results.find_one({"execution_id": execution_id})
                return ExecutionResult(
                    output=result["data"] if result else "",
                    status=execution["status"],
                    error=execution.get("error")
                )

            await asyncio.sleep(poll_interval)

        # Timeout
        from datetime import datetime, timezone
        db.executions.update_one(
            {"_id": execution_id},
            {"$set": {"status": "timeout", "completed_at": datetime.now(timezone.utc)}}
        )
        logger.warning(f"[{execution_id}] Execution timed out after {timeout}s")
        return ExecutionResult(status="timeout", error=f"Timeout after {timeout}s")
