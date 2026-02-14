#!/usr/bin/env python3
"""
AIAgentHub - Main server entry point

Runs: FastAPI server + Scheduler + Worker loop
Port: 9100
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import uvicorn

from aiagent.config import settings
from aiagent.database import get_db
from aiagent.engine.scheduler import get_scheduler
from aiagent.engine.worker_loop import get_worker_loop
from aiagent.api import agents, prompts, executions, chains, results, workers, schedules, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    logger.info("=" * 60)
    logger.info("AIAgentHub starting...")
    logger.info(f"Node: {settings.get_node_id()}")
    logger.info("=" * 60)

    # Initialize database
    db = get_db()
    db.ensure_indexes()

    # Register this node as a worker
    from aiagent.api.workers import register_worker
    await register_worker()

    # Start scheduler
    scheduler = get_scheduler()
    await scheduler.start()

    # Start worker loop (claims and executes tasks)
    worker = get_worker_loop()
    await worker.start()

    logger.info(f"Server ready on port {settings.api_port}")
    logger.info(f"API docs: http://localhost:{settings.api_port}/docs")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("Shutting down...")
    await scheduler.stop()
    await worker.stop()
    db.close()


app = FastAPI(
    title="AIAgentHub",
    description="Universal AI Agent Platform - tmux + MongoDB + Chain execution",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(agents.router)
app.include_router(prompts.router)
app.include_router(executions.router)
app.include_router(chains.router)
app.include_router(results.router)
app.include_router(workers.router)
app.include_router(schedules.router)
app.include_router(system.router)


@app.get("/")
async def root():
    return {
        "service": "AIAgentHub",
        "version": "1.0.0",
        "node": settings.get_node_id(),
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    db = get_db()
    try:
        db.db.command("ping")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {e}"

    return {"status": "healthy", "database": db_status, "node": settings.get_node_id()}


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=True,
        log_level="info",
    )
