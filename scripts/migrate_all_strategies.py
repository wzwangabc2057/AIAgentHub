#!/usr/bin/env python3
"""
Migrate all 3 trading strategies from trading-arena to AIAgentHub:
1. duanban_001 - 断板反包 (4 phases)
2. yijiner_001 - 一进二 (4 phases) - already done, skip if exists
3. sector_001 - 板块分析 (2 phases)
"""

import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from aiagent.database import get_db
from aiagent.config import settings

ARENA_BASE = "/Users/kangbing/112/pythontest/brain/trading-arena"


def create_agent(db, agent_id, name, description, node_id, now):
    agent = {
        "_id": agent_id,
        "name": name,
        "description": description,
        "status": "active",
        "node_id": node_id,
        "config": {"timeout": 600, "execution_mode": "print"},
        "created_at": now,
        "updated_at": now,
    }
    db.agents.update_one({"_id": agent_id}, {"$set": agent}, upsert=True)
    print(f"  Agent: {agent_id} ({name})")


def copy_agent_files(agent_id, files):
    work_dir = os.path.join(os.path.abspath(settings.agents_dir), agent_id)
    os.makedirs(work_dir, exist_ok=True)
    for filename in files:
        src = os.path.join(ARENA_BASE, f"agents/{agent_id}/{filename}")
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(work_dir, filename))
            print(f"    Copied {filename}")
    # Also copy SKILLS_FULL.md and RULES_API.md if they exist
    for extra in ["SKILLS_FULL.md", "RULES_API.md"]:
        src = os.path.join(ARENA_BASE, f"agents/{agent_id}/{extra}")
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(work_dir, extra))
            print(f"    Copied {extra}")


def import_prompt(db, prompt_id, agent_id, name, filepath, now):
    if not os.path.exists(filepath):
        print(f"    SKIP: {filepath} not found")
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    prompt = {
        "_id": prompt_id,
        "agent_id": agent_id,
        "name": name,
        "content": content,
        "variables": [],
        "version": 1,
        "created_at": now,
        "updated_at": now,
    }
    db.prompts.update_one({"_id": prompt_id}, {"$set": prompt}, upsert=True)
    print(f"    Prompt: {prompt_id} ({len(content)} chars)")


def migrate():
    db = get_db()
    db.ensure_indexes()
    node_id = settings.get_node_id()
    now = datetime.now(timezone.utc)

    print("=" * 60)
    print("Migrating trading-arena strategies to AIAgentHub")
    print("=" * 60)

    # =============================================
    # 1. 断板反包 (duanban_001)
    # =============================================
    print("\n[1/3] 断板反包 (duanban_001)")
    create_agent(db, "duanban_001", "断板反包专家", "断板反包分级打法 - 含盘前/竞价/盘中/复盘四阶段", node_id, now)
    copy_agent_files("duanban_001", ["CLAUDE.md", "methodology.md"])

    prompts_base = os.path.join(ARENA_BASE, "prompts")
    import_prompt(db, "duanban_pre_market", "duanban_001", "断板盘前分析",
                  os.path.join(prompts_base, "pre_market.txt"), now)
    import_prompt(db, "duanban_auction", "duanban_001", "断板集合竞价",
                  os.path.join(prompts_base, "auction.txt"), now)
    import_prompt(db, "duanban_intraday", "duanban_001", "断板盘中监控",
                  os.path.join(prompts_base, "intraday.txt"), now)
    import_prompt(db, "duanban_summary", "duanban_001", "断板盘后复盘",
                  os.path.join(prompts_base, "summary.txt"), now)

    # =============================================
    # 2. 一进二 (yijiner_001) - check if already migrated
    # =============================================
    print("\n[2/3] 一进二 (yijiner_001)")
    create_agent(db, "yijiner_001", "一进二策略专家", "首板晋级二板策略 - 小盘热门优先", node_id, now)
    copy_agent_files("yijiner_001", ["CLAUDE.md", "methodology.md"])

    yijiner_base = os.path.join(prompts_base, "yijiner")
    import_prompt(db, "yijiner_pre_market", "yijiner_001", "一进二盘前分析",
                  os.path.join(yijiner_base, "pre_market.txt"), now)
    import_prompt(db, "yijiner_auction", "yijiner_001", "一进二集合竞价",
                  os.path.join(yijiner_base, "auction.txt"), now)
    import_prompt(db, "yijiner_intraday", "yijiner_001", "一进二盘中监控",
                  os.path.join(yijiner_base, "intraday.txt"), now)
    import_prompt(db, "yijiner_summary", "yijiner_001", "一进二盘后复盘",
                  os.path.join(yijiner_base, "summary.txt"), now)

    # =============================================
    # 3. 板块分析 (sector_001)
    # =============================================
    print("\n[3/3] 板块分析 (sector_001)")
    create_agent(db, "sector_001", "板块分析专家", "板块轮动分析 - 热度跟踪/龙头识别/轮动预判", node_id, now)
    copy_agent_files("sector_001", ["CLAUDE.md", "methodology.md"])

    sector_base = os.path.join(prompts_base, "sector")
    import_prompt(db, "sector_pre_market", "sector_001", "板块盘前分析",
                  os.path.join(sector_base, "pre_market.txt"), now)
    import_prompt(db, "sector_summary", "sector_001", "板块盘后总结",
                  os.path.join(sector_base, "summary.txt"), now)

    # =============================================
    # 4. Create schedules
    # =============================================
    print("\n[Schedules]")

    schedules = [
        {
            "_id": "duanban_daily",
            "name": "断板反包每日流程",
            "type": "cron",
            "cron": "30 8 * * 1-5",
            "target": {
                "type": "chain",
                "chain_template": {
                    "name": "断板反包日常流水线",
                    "steps": [
                        {"step": 1, "agent_id": "duanban_001", "prompt_id": "duanban_pre_market", "timeout": 600},
                        {"step": 2, "agent_id": "duanban_001", "prompt_id": "duanban_auction", "timeout": 900},
                        {"step": 3, "agent_id": "duanban_001", "prompt_id": "duanban_intraday", "timeout": 3600},
                        {"step": 4, "agent_id": "duanban_001", "prompt_id": "duanban_summary", "timeout": 600},
                    ]
                }
            },
            "enabled": False,
            "last_run": None,
            "created_at": now,
        },
        {
            "_id": "yijiner_daily",
            "name": "一进二每日流程",
            "type": "cron",
            "cron": "30 8 * * 1-5",
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
        },
        {
            "_id": "sector_daily",
            "name": "板块分析每日流程",
            "type": "cron",
            "cron": "25 8 * * 1-5",
            "target": {
                "type": "chain",
                "chain_template": {
                    "name": "板块分析日常流水线",
                    "steps": [
                        {"step": 1, "agent_id": "sector_001", "prompt_id": "sector_pre_market", "timeout": 600},
                        {"step": 2, "agent_id": "sector_001", "prompt_id": "sector_summary", "timeout": 600},
                    ]
                }
            },
            "enabled": False,
            "last_run": None,
            "created_at": now,
        },
    ]

    for sched in schedules:
        db.schedules.update_one({"_id": sched["_id"]}, {"$set": sched}, upsert=True)
        print(f"  Schedule: {sched['_id']} ({sched['name']})")

    # =============================================
    # Summary
    # =============================================
    agent_count = db.agents.count_documents({"_id": {"$in": ["duanban_001", "yijiner_001", "sector_001"]}})
    prompt_count = db.prompts.count_documents({"agent_id": {"$in": ["duanban_001", "yijiner_001", "sector_001"]}})

    print(f"\n{'='*60}")
    print(f"Migration complete!")
    print(f"  Agents: {agent_count}")
    print(f"  Prompts: {prompt_count}")
    print(f"  Schedules: {len(schedules)}")
    print(f"\n--- Quick Test Commands ---")
    print(f"# Run yijiner pre-market (一进二盘前分析)")
    print(f'curl -X POST http://localhost:9100/api/execute/yijiner_001 \\')
    print(f'  -H "Content-Type: application/json" \\')
    print(f'  -d \'{{"prompt_id":"yijiner_pre_market","timeout":600}}\'')
    print(f"")
    print(f"# Attach to watch execution")
    print(f"tmux attach -t aah_yijiner_001")


if __name__ == "__main__":
    migrate()
