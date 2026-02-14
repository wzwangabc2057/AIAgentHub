#!/usr/bin/env python3
"""
Migrate yijiner_001 (一进二策略) from trading-arena to AIAgentHub

Creates:
- Agent: yijiner_001
- 4 Prompt templates: pre_market, auction, intraday, summary
- CLAUDE.md in agent work directory
- 1 Chain template schedule (daily workflow)
"""

import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from aiagent.database import get_db
from aiagent.config import settings

ARENA_BASE = "/Users/kangbing/112/pythontest/brain/trading-arena"


def migrate():
    db = get_db()
    db.ensure_indexes()
    node_id = settings.get_node_id()
    now = datetime.now(timezone.utc)

    # === 1. Create Agent ===
    agent = {
        "_id": "yijiner_001",
        "name": "一进二策略专家",
        "description": "首板晋级二板策略 - 小盘热门优先，含盘前/竞价/盘中/复盘四阶段",
        "status": "active",
        "node_id": node_id,
        "config": {"timeout": 600, "execution_mode": "print"},
        "created_at": now,
        "updated_at": now,
    }
    db.agents.update_one({"_id": agent["_id"]}, {"$set": agent}, upsert=True)
    print("Agent created: yijiner_001")

    # === 2. Copy CLAUDE.md + methodology ===
    work_dir = os.path.join(os.path.abspath(settings.agents_dir), "yijiner_001")
    os.makedirs(work_dir, exist_ok=True)

    src_claude = os.path.join(ARENA_BASE, "agents/yijiner_001/CLAUDE.md")
    if os.path.exists(src_claude):
        shutil.copy2(src_claude, os.path.join(work_dir, "CLAUDE.md"))
        print(f"  Copied CLAUDE.md")

    src_method = os.path.join(ARENA_BASE, "agents/yijiner_001/methodology.md")
    if os.path.exists(src_method):
        shutil.copy2(src_method, os.path.join(work_dir, "methodology.md"))
        print(f"  Copied methodology.md")

    # === 3. Import Prompt Templates ===
    prompts_dir = os.path.join(ARENA_BASE, "prompts/yijiner")
    prompt_files = {
        "yijiner_pre_market": ("pre_market.txt", "一进二盘前分析"),
        "yijiner_auction": ("auction.txt", "一进二集合竞价"),
        "yijiner_intraday": ("intraday.txt", "一进二盘中监控"),
        "yijiner_summary": ("summary.txt", "一进二盘后复盘"),
    }

    for prompt_id, (filename, name) in prompt_files.items():
        filepath = os.path.join(prompts_dir, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP: {filepath} not found")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        prompt = {
            "_id": prompt_id,
            "agent_id": "yijiner_001",
            "name": name,
            "content": content,
            "variables": [],
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }
        db.prompts.update_one({"_id": prompt_id}, {"$set": prompt}, upsert=True)
        print(f"  Prompt imported: {prompt_id} ({len(content)} chars)")

    # === 4. Create Daily Chain Schedule ===
    schedule = {
        "_id": "yijiner_daily",
        "name": "一进二每日流程",
        "type": "cron",
        "cron": "30 8 * * 1-5",  # 8:30 weekdays
        "target": {
            "type": "chain",
            "chain_template": {
                "name": "一进二日常流水线",
                "steps": [
                    {"step": 1, "agent_id": "yijiner_001", "prompt_id": "yijiner_pre_market", "timeout": 600},
                    {"step": 2, "agent_id": "yijiner_001", "prompt_id": "yijiner_auction", "timeout": 900},
                    {"step": 3, "agent_id": "yijiner_001", "prompt_id": "yijiner_intraday", "timeout": 3600},
                    {"step": 4, "agent_id": "yijiner_001", "prompt_id": "yijiner_summary", "timeout": 600},
                ]
            }
        },
        "enabled": False,
        "last_run": None,
        "created_at": now,
    }
    db.schedules.update_one({"_id": schedule["_id"]}, {"$set": schedule}, upsert=True)
    print("  Schedule created: yijiner_daily (disabled)")

    # === 5. Summary ===
    print(f"\n{'='*50}")
    print("Migration complete!")
    print(f"  Agent: yijiner_001")
    print(f"  Prompts: {len(prompt_files)} imported")
    print(f"  Work dir: {work_dir}")
    print(f"  Schedule: yijiner_daily (cron: 8:30 weekdays)")
    print(f"\nTest commands:")
    print(f"  # Start server")
    print(f"  python server.py")
    print(f"")
    print(f"  # Run pre-market analysis")
    print(f'  curl -X POST http://localhost:9100/api/execute/yijiner_001 \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{{"prompt_id":"yijiner_pre_market","timeout":600}}\'')
    print(f"")
    print(f"  # Or run full daily chain")
    print(f'  curl -X POST http://localhost:9100/api/chains \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{{"name":"一进二测试","steps":[')
    print(f'      {{"agent_id":"yijiner_001","prompt_id":"yijiner_pre_market","timeout":600}}')
    print(f'    ]}}\'')
    print(f"")
    print(f"  # Watch execution")
    print(f"  tmux attach -t aah_yijiner_001")


if __name__ == "__main__":
    migrate()
