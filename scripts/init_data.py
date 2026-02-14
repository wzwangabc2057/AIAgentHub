#!/usr/bin/env python3
"""
Initialize AIAgentHub with sample data for testing.

Creates:
- 2 sample agents (researcher_001, writer_001)
- 2 prompt templates
- 1 sample schedule
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from aiagent.database import get_db
from aiagent.config import settings


def init():
    db = get_db()
    db.ensure_indexes()
    node_id = settings.get_node_id()
    now = datetime.now(timezone.utc)

    # --- Agents ---
    agents = [
        {
            "_id": "researcher_001",
            "name": "Research Agent",
            "description": "Researches topics and produces findings",
            "status": "active",
            "node_id": node_id,
            "config": {"timeout": 300, "execution_mode": "print"},
            "created_at": now,
            "updated_at": now,
        },
        {
            "_id": "writer_001",
            "name": "Writer Agent",
            "description": "Writes reports and articles based on research",
            "status": "active",
            "node_id": node_id,
            "config": {"timeout": 300, "execution_mode": "print"},
            "created_at": now,
            "updated_at": now,
        },
    ]

    for agent in agents:
        db.agents.update_one({"_id": agent["_id"]}, {"$set": agent}, upsert=True)
        # Create work directory
        work_dir = os.path.join(os.path.abspath(settings.agents_dir), agent["_id"])
        os.makedirs(work_dir, exist_ok=True)
        claude_md = os.path.join(work_dir, "CLAUDE.md")
        if not os.path.exists(claude_md):
            with open(claude_md, "w") as f:
                f.write(f"# {agent['name']}\n\n{agent['description']}\n")

    print(f"Created {len(agents)} agents")

    # --- Prompts ---
    prompts = [
        {
            "_id": "p_research",
            "agent_id": "researcher_001",
            "name": "Research Topic",
            "content": "研究{topic}的最新趋势，输出关键发现。要求：\n1. 列出至少3个关键趋势\n2. 每个趋势附带简要分析\n3. 给出总结",
            "variables": ["topic"],
            "version": 1,
            "created_at": now,
            "updated_at": now,
        },
        {
            "_id": "p_write",
            "agent_id": "writer_001",
            "name": "Write Report",
            "content": "根据以下研究结果，写一篇结构化的分析报告：\n\n{research_input}\n\n要求：\n1. 有清晰的标题和摘要\n2. 分章节论述\n3. 给出结论和建议",
            "variables": ["research_input"],
            "version": 1,
            "created_at": now,
            "updated_at": now,
        },
    ]

    for prompt in prompts:
        db.prompts.update_one({"_id": prompt["_id"]}, {"$set": prompt}, upsert=True)

    print(f"Created {len(prompts)} prompts")

    # --- Sample Schedule ---
    schedule = {
        "_id": "daily_research",
        "name": "Daily AI Research",
        "type": "cron",
        "cron": "0 9 * * 1-5",
        "target": {
            "type": "chain",
            "chain_template": {
                "name": "Daily Research Pipeline",
                "steps": [
                    {"step": 1, "agent_id": "researcher_001", "prompt_id": "p_research", "variables": {"topic": "AI Agent"}},
                    {"step": 2, "agent_id": "writer_001", "prompt_id": "p_write", "variables": {"research_input": "{step_1_output}"}},
                ]
            }
        },
        "enabled": False,  # Disabled by default
        "last_run": None,
        "created_at": now,
    }
    db.schedules.update_one({"_id": schedule["_id"]}, {"$set": schedule}, upsert=True)
    print("Created 1 schedule (disabled)")

    # --- Register Worker ---
    import socket
    db.workers.update_one(
        {"_id": node_id},
        {"$set": {
            "hostname": socket.gethostname(),
            "capacity": settings.max_concurrent,
            "agents": [a["_id"] for a in agents],
            "status": "offline",
            "last_heartbeat": now,
            "started_at": now,
        }},
        upsert=True
    )
    print(f"Registered worker: {node_id}")

    print("\nInit complete! Start server with: python server.py")


if __name__ == "__main__":
    init()
