"""
Worker loop - distributed task claiming and execution

Core distributed component:
- Polls MongoDB for pending tasks assigned to this node's agents
- Uses atomic findOneAndUpdate for conflict-free task claiming
- Sends heartbeat to workers collection
- Executes claimed tasks via ExecutorPool
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, List
from loguru import logger
from pymongo import ReturnDocument

from aiagent.config import settings
from aiagent.database import get_db
from aiagent.engine.executor_pool import get_executor_pool


class WorkerLoop:
    """Worker that polls MongoDB and claims tasks for local execution"""

    def __init__(self, node_id: Optional[str] = None):
        self.node_id = node_id or settings.get_node_id()
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    def _get_my_agents(self) -> List[str]:
        """Get agent IDs assigned to this node"""
        db = get_db()
        agents = db.agents.find({"node_id": self.node_id, "status": "active"})
        return [a["_id"] for a in agents]

    async def start(self):
        """Start the worker loop"""
        if self._running:
            return

        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Worker loop started: node={self.node_id}")

    async def stop(self):
        """Stop the worker loop"""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        logger.info("Worker loop stopped")

    async def _poll_loop(self):
        """Main polling loop - claim and execute pending tasks"""
        pool = get_executor_pool()

        while self._running:
            try:
                my_agents = self._get_my_agents()
                if not my_agents:
                    await asyncio.sleep(settings.worker_poll_interval)
                    continue

                task = self._claim_task(my_agents)
                if task:
                    # Execute in background (don't block polling)
                    asyncio.create_task(self._execute_task(task, pool))
                else:
                    await asyncio.sleep(settings.worker_poll_interval)

            except Exception as e:
                logger.exception(f"Worker poll error: {e}")
                await asyncio.sleep(settings.worker_poll_interval)

    def _claim_task(self, my_agents: List[str]) -> Optional[dict]:
        """Atomically claim a pending task for this node's agents"""
        db = get_db()
        now = datetime.now(timezone.utc)

        task = db.executions.find_one_and_update(
            {
                "status": "pending",
                "agent_id": {"$in": my_agents},
            },
            {
                "$set": {
                    "status": "running",
                    "node_id": self.node_id,
                    "started_at": now,
                }
            },
            return_document=ReturnDocument.AFTER
        )

        if task:
            logger.info(f"Worker claimed task: {task['_id']} for agent {task['agent_id']}")
        return task

    async def _execute_task(self, task: dict, pool):
        """Execute a claimed task"""
        execution_id = task["_id"]
        agent_id = task["agent_id"]
        prompt = task.get("prompt_content", "")
        timeout = task.get("timeout", settings.default_timeout)

        if not prompt:
            logger.error(f"Task {execution_id} has no prompt content")
            db = get_db()
            db.executions.update_one(
                {"_id": execution_id},
                {"$set": {"status": "failed", "error": "No prompt content"}}
            )
            return

        try:
            result = await pool.execute(execution_id, agent_id, prompt, timeout)
            logger.info(f"Task {execution_id} completed: {result.status}")
        except Exception as e:
            logger.exception(f"Task {execution_id} failed: {e}")
            db = get_db()
            db.executions.update_one(
                {"_id": execution_id},
                {"$set": {
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now(timezone.utc),
                }}
            )

    async def _heartbeat_loop(self):
        """Send periodic heartbeat to MongoDB"""
        db = get_db()

        while self._running:
            try:
                now = datetime.now(timezone.utc)
                my_agents = self._get_my_agents()

                db.workers.update_one(
                    {"_id": self.node_id},
                    {"$set": {
                        "last_heartbeat": now,
                        "status": "online",
                        "agents": my_agents,
                    }},
                    upsert=True
                )
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

            await asyncio.sleep(settings.heartbeat_interval)


# Global instance
_worker: Optional[WorkerLoop] = None


def get_worker_loop(node_id: Optional[str] = None) -> WorkerLoop:
    global _worker
    if _worker is None:
        _worker = WorkerLoop(node_id)
    return _worker
