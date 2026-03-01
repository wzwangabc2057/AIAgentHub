"""
Chain executor - multi-agent pipeline orchestration

Responsibilities:
1. Variable resolution: substitute {step_N_output} placeholders with actual outputs
2. Completion waiting: poll MongoDB for Claude's done callback
3. Step orchestration: manage sequential and parallel steps
4. Dependency tracking: steps with depends_on wait for dependencies to complete
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from loguru import logger

from aiagent.config import settings
from aiagent.database import get_db
from aiagent.engine.executor_pool import get_executor_pool
from aiagent.engine.prompt_renderer import render_prompt


class ChainExecutor:
    """Orchestrate multi-step chain execution with dependency tracking"""

    async def start_chain(self, chain_id: str) -> None:
        """Start executing a chain (runs as background task)"""
        db = get_db()

        chain = db.chains.find_one({"_id": chain_id})
        if not chain:
            logger.error(f"Chain {chain_id} not found")
            return

        # Update chain status
        db.chains.update_one(
            {"_id": chain_id},
            {"$set": {"status": "running", "started_at": datetime.now(timezone.utc)}}
        )

        logger.info(f"Chain {chain_id} started: {chain['name']} ({len(chain['steps'])} steps)")

        try:
            await self._execute_steps(chain_id, chain["steps"])

            # Check final status
            chain = db.chains.find_one({"_id": chain_id})
            all_completed = all(s["status"] == "completed" for s in chain["steps"])

            if all_completed:
                db.chains.update_one(
                    {"_id": chain_id},
                    {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc)}}
                )
                logger.info(f"Chain {chain_id} completed successfully")
            else:
                failed_steps = [s["step"] for s in chain["steps"] if s["status"] in ("failed", "timeout")]
                db.chains.update_one(
                    {"_id": chain_id},
                    {"$set": {
                        "status": "failed",
                        "completed_at": datetime.now(timezone.utc),
                        "error": f"Steps {failed_steps} failed"
                    }}
                )
                logger.error(f"Chain {chain_id} failed at steps {failed_steps}")

        except Exception as e:
            logger.exception(f"Chain {chain_id} error: {e}")
            db.chains.update_one(
                {"_id": chain_id},
                {"$set": {
                    "status": "failed",
                    "completed_at": datetime.now(timezone.utc),
                    "error": str(e)
                }}
            )

    async def _execute_steps(self, chain_id: str, steps: List[dict]) -> None:
        """Execute steps respecting dependencies. Steps without dependencies can run in parallel."""
        db = get_db()
        pool = get_executor_pool()

        completed_steps: Set[int] = set()
        step_outputs: Dict[int, str] = {}  # step_number -> output text
        running_tasks: Dict[int, asyncio.Task] = {}

        # Build step lookup
        step_map = {s["step"]: s for s in steps}
        total_steps = len(steps)

        while len(completed_steps) < total_steps:
            # Check for cancelled chain
            chain = db.chains.find_one({"_id": chain_id})
            if chain and chain["status"] == "cancelled":
                logger.info(f"Chain {chain_id} was cancelled")
                # Cancel running tasks
                for task in running_tasks.values():
                    task.cancel()
                return

            # Find ready steps (all dependencies completed, not yet started)
            ready_steps = []
            for step_num, step in step_map.items():
                if step_num in completed_steps:
                    continue
                if step_num in running_tasks:
                    continue
                if step["status"] in ("failed", "timeout"):
                    completed_steps.add(step_num)
                    continue

                depends = step.get("depends_on", [])
                if not depends:
                    # No dependencies - check if it's sequential (depends on previous step)
                    if step_num == 1 or (step_num - 1) in completed_steps or any(s["step"] < step_num and s.get("depends_on") is not None for s in steps):
                        ready_steps.append(step_num)
                elif all(d in completed_steps for d in depends):
                    ready_steps.append(step_num)

            # Launch ready steps
            for step_num in ready_steps:
                step = step_map[step_num]
                task = asyncio.create_task(
                    self._execute_single_step(chain_id, step, step_outputs, pool)
                )
                running_tasks[step_num] = task

            # Wait for any running task to complete
            if running_tasks:
                active_tasks = {sn: t for sn, t in running_tasks.items() if sn not in completed_steps}
                if active_tasks:
                    done, _ = await asyncio.wait(
                        active_tasks.values(),
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    for completed_task in done:
                        # Find which step this was
                        for sn, t in list(running_tasks.items()):
                            if t == completed_task:
                                try:
                                    output = completed_task.result()
                                    step_outputs[sn] = output
                                    completed_steps.add(sn)
                                    del running_tasks[sn]
                                    logger.info(f"Chain {chain_id} step {sn} completed")
                                except Exception as e:
                                    completed_steps.add(sn)
                                    del running_tasks[sn]
                                    logger.error(f"Chain {chain_id} step {sn} error: {e}")
                                break
            else:
                # No running tasks and no ready steps - might be stuck
                if not ready_steps:
                    logger.error(f"Chain {chain_id} stuck: no ready steps and no running tasks")
                    break
                await asyncio.sleep(1)

    async def _execute_single_step(
        self,
        chain_id: str,
        step: dict,
        step_outputs: Dict[int, str],
        pool,
    ) -> str:
        """Execute a single chain step and return its output"""
        db = get_db()
        step_num = step["step"]
        agent_id = step["agent_id"]
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"

        # Update chain step status
        db.chains.update_one(
            {"_id": chain_id, "steps.step": step_num},
            {"$set": {
                "steps.$.status": "running",
                "steps.$.execution_id": execution_id,
                "current_step": step_num,
            }}
        )

        # Get prompt content
        prompt_content = step.get("inline_prompt", "")
        if not prompt_content and step.get("prompt_id"):
            prompt_doc = db.prompts.find_one({"_id": step["prompt_id"]})
            if prompt_doc:
                prompt_content = prompt_doc["content"]
            else:
                raise ValueError(f"Prompt {step['prompt_id']} not found")

        # Render prompt with variables and chain outputs
        rendered = render_prompt(
            template=prompt_content,
            variables=step.get("variables", {}),
            execution_id=execution_id,
            agent_id=agent_id,
            step=step_num,
            step_outputs=step_outputs,
        )

        # Create execution record
        db.executions.insert_one({
            "_id": execution_id,
            "agent_id": agent_id,
            "chain_id": chain_id,
            "step": step_num,
            "prompt_content": rendered,
            "status": "pending",
            "timeout": step.get("timeout", settings.default_timeout),
            "created_at": datetime.now(timezone.utc),
        })

        # Execute via pool
        result = await pool.execute(
            execution_id=execution_id,
            agent_id=agent_id,
            prompt=rendered,
            timeout=step.get("timeout", settings.default_timeout),
        )

        # Update chain step status
        db.chains.update_one(
            {"_id": chain_id, "steps.step": step_num},
            {"$set": {"steps.$.status": result.status}}
        )

        if result.status != "completed":
            raise RuntimeError(f"Step {step_num} {result.status}: {result.error}")

        return result.output


# Global instance
_chain_executor: Optional[ChainExecutor] = None


def get_chain_executor() -> ChainExecutor:
    global _chain_executor
    if _chain_executor is None:
        _chain_executor = ChainExecutor()
    return _chain_executor
