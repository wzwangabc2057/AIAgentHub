"""
Scheduler - cron, interval, and event-based trigger system

Polls MongoDB schedules collection and triggers executions/chains
based on cron expressions, intervals, or events.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from croniter import croniter

from aiagent.config import settings
from aiagent.database import get_db


class Scheduler:
    """Cron/interval/event scheduler for automated execution"""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the scheduler loop"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Scheduler started")

    async def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Scheduler stopped")

    async def _loop(self):
        """Main scheduler loop - check schedules every 10 seconds"""
        while self._running:
            try:
                await self._check_schedules()
            except Exception as e:
                logger.exception(f"Scheduler error: {e}")
            await asyncio.sleep(10)

    async def _check_schedules(self):
        """Check all enabled schedules and trigger if due"""
        db = get_db()
        now = datetime.now(timezone.utc)

        schedules = list(db.schedules.find({"enabled": True}))
        for schedule in schedules:
            try:
                should_run = False

                if schedule["type"] == "cron" and schedule.get("cron"):
                    should_run = self._check_cron(schedule, now)
                elif schedule["type"] == "interval" and schedule.get("interval_seconds"):
                    should_run = self._check_interval(schedule, now)

                if should_run:
                    logger.info(f"Triggering schedule: {schedule['_id']}")
                    await self.trigger_schedule(schedule)
                    db.schedules.update_one(
                        {"_id": schedule["_id"]},
                        {"$set": {"last_run": now}}
                    )
            except Exception as e:
                logger.error(f"Error checking schedule {schedule['_id']}: {e}")

    def _check_cron(self, schedule: dict, now: datetime) -> bool:
        """Check if cron schedule is due"""
        cron_expr = schedule["cron"]
        last_run = schedule.get("last_run")

        if last_run is None:
            # Never run before - check if current time matches
            cron = croniter(cron_expr, now)
            prev = cron.get_prev(datetime)
            # If the previous match was within last 15 seconds, trigger
            return (now - prev.replace(tzinfo=timezone.utc)).total_seconds() < 15

        cron = croniter(cron_expr, last_run)
        next_run = cron.get_next(datetime).replace(tzinfo=timezone.utc)
        return now >= next_run

    def _check_interval(self, schedule: dict, now: datetime) -> bool:
        """Check if interval schedule is due"""
        interval = schedule["interval_seconds"]
        last_run = schedule.get("last_run")

        if last_run is None:
            return True

        elapsed = (now - last_run).total_seconds()
        return elapsed >= interval

    async def trigger_schedule(self, schedule: dict):
        """Execute the schedule's target"""
        target = schedule.get("target", {})
        target_type = target.get("type", "execute")

        if target_type == "chain":
            await self._trigger_chain(target)
        elif target_type == "execute":
            await self._trigger_execute(target)

    async def _trigger_chain(self, target: dict):
        """Trigger a chain from schedule"""
        from aiagent.engine.chain_executor import get_chain_executor

        db = get_db()
        chain_template = target.get("chain_template", {})
        chain_id = f"chain_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        steps = chain_template.get("steps", [])
        for i, step in enumerate(steps):
            if not step.get("step"):
                step["step"] = i + 1
            step["status"] = "pending"
            step["execution_id"] = None
            if not step.get("depends_on") and step["step"] > 1:
                step["depends_on"] = [step["step"] - 1]

        chain = {
            "_id": chain_id,
            "name": chain_template.get("name", f"scheduled_{chain_id}"),
            "status": "pending",
            "current_step": None,
            "steps": steps,
            "created_at": now,
        }
        db.chains.insert_one(chain)

        executor = get_chain_executor()
        asyncio.create_task(executor.start_chain(chain_id))
        logger.info(f"Schedule triggered chain: {chain_id}")

    async def _trigger_execute(self, target: dict):
        """Trigger a single execution from schedule"""
        from aiagent.engine.executor_pool import get_executor_pool
        from aiagent.engine.prompt_renderer import render_prompt

        db = get_db()
        agent_id = target.get("agent_id")
        prompt_id = target.get("prompt_id")
        variables = target.get("variables", {})
        timeout = target.get("timeout", settings.default_timeout)

        if not agent_id:
            logger.error("Schedule target missing agent_id")
            return

        prompt_content = ""
        if prompt_id:
            prompt = db.prompts.find_one({"_id": prompt_id})
            if prompt:
                prompt_content = prompt["content"]
        elif target.get("inline_prompt"):
            prompt_content = target["inline_prompt"]

        if not prompt_content:
            logger.error(f"Schedule target has no prompt for agent {agent_id}")
            return

        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        rendered = render_prompt(
            template=prompt_content,
            variables=variables,
            execution_id=execution_id,
            agent_id=agent_id,
        )

        now = datetime.now(timezone.utc)
        db.executions.insert_one({
            "_id": execution_id,
            "agent_id": agent_id,
            "prompt_id": prompt_id,
            "prompt_content": rendered,
            "status": "pending",
            "timeout": timeout,
            "node_id": settings.get_node_id(),
            "created_at": now,
        })

        pool = get_executor_pool()
        asyncio.create_task(pool.execute(execution_id, agent_id, rendered, timeout))
        logger.info(f"Schedule triggered execution: {execution_id} for {agent_id}")

    def get_status(self) -> dict:
        return {"running": self._running}


# Global instance
_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler
