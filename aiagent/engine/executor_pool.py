"""
Executor pool - concurrent execution management

Controls concurrency:
- Global semaphore: limits total concurrent agents (default max=8)
- Per-agent lock: ensures same agent runs only one task at a time
- Different agents can run in parallel across different pipelines
"""

import asyncio
from typing import Dict, Optional
from loguru import logger

from aiagent.config import settings
from aiagent.engine.tmux_executor import TmuxExecutor, ExecutionResult


class ExecutorPool:
    """Manage concurrent agent execution: different agents parallel, same agent serial"""

    def __init__(self, max_concurrent: Optional[int] = None):
        self.max_concurrent = max_concurrent or settings.max_concurrent
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._agent_locks: Dict[str, asyncio.Lock] = {}
        self._executor = TmuxExecutor()
        logger.info(f"ExecutorPool initialized: max_concurrent={self.max_concurrent}")

    def _get_agent_lock(self, agent_id: str) -> asyncio.Lock:
        """Get or create a lock for an agent"""
        if agent_id not in self._agent_locks:
            self._agent_locks[agent_id] = asyncio.Lock()
        return self._agent_locks[agent_id]

    async def execute(
        self,
        execution_id: str,
        agent_id: str,
        prompt: str,
        timeout: int = 300,
    ) -> ExecutionResult:
        """
        Execute with concurrency control.

        1. Acquire global semaphore slot (limits total concurrent agents)
        2. Acquire per-agent lock (same agent runs serially)
        3. Execute via TmuxExecutor
        """
        logger.info(f"[{execution_id}] Queued for {agent_id} (pool: {self.max_concurrent - self._semaphore._value}/{self.max_concurrent} busy)")

        async with self._semaphore:
            lock = self._get_agent_lock(agent_id)
            logger.info(f"[{execution_id}] Acquired pool slot, waiting for agent lock: {agent_id}")

            async with lock:
                logger.info(f"[{execution_id}] Executing on {agent_id}")
                return await self._executor.execute(execution_id, agent_id, prompt, timeout)

    @property
    def active_count(self) -> int:
        """Number of currently active executions"""
        return self.max_concurrent - self._semaphore._value

    def get_status(self) -> dict:
        """Get pool status"""
        locked_agents = [aid for aid, lock in self._agent_locks.items() if lock.locked()]
        return {
            "max_concurrent": self.max_concurrent,
            "active": self.active_count,
            "available": self._semaphore._value,
            "locked_agents": locked_agents,
        }


# Global pool instance
_pool: Optional[ExecutorPool] = None


def get_executor_pool() -> ExecutorPool:
    global _pool
    if _pool is None:
        _pool = ExecutorPool()
    return _pool
