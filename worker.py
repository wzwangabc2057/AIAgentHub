#!/usr/bin/env python3
"""
AIAgentHub - Worker node entry point

Runs: Worker loop only (no API server, no scheduler)
Used for distributed deployment where this node only claims and executes tasks.
"""

import asyncio
import signal
import sys
from loguru import logger

from aiagent.config import settings
from aiagent.database import get_db
from aiagent.engine.worker_loop import get_worker_loop


async def main():
    node_id = settings.get_node_id()
    logger.info("=" * 60)
    logger.info(f"AIAgentHub Worker starting: {node_id}")
    logger.info(f"MongoDB: {settings.mongo_uri}")
    logger.info("=" * 60)

    # Initialize database
    db = get_db()
    db.ensure_indexes()

    # Register as worker
    import socket
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    my_agents = [a["_id"] for a in db.agents.find({"node_id": node_id, "status": "active"})]

    db.workers.update_one(
        {"_id": node_id},
        {"$set": {
            "hostname": socket.gethostname(),
            "capacity": settings.max_concurrent,
            "agents": my_agents,
            "status": "online",
            "last_heartbeat": now,
            "started_at": now,
        }},
        upsert=True
    )

    # Start worker loop
    worker = get_worker_loop(node_id)
    await worker.start()

    logger.info(f"Worker ready: {node_id} (agents: {my_agents})")

    # Wait for shutdown signal
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await stop_event.wait()

    # Cleanup
    await worker.stop()
    db.workers.update_one({"_id": node_id}, {"$set": {"status": "offline"}})
    db.close()
    logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
