from __future__ import annotations

from typing import Any


def split_questions(goal: str) -> list[str]:
    """Simple deterministic decomposition to keep behavior stable."""
    templates = [
        "这个目标的核心判断条件是什么？",
        "当前已有数据中最支持与最反对该目标的证据分别是什么？",
        "执行该目标的风险、失效条件和撤退条件是什么？",
        "如果要在今天给出行动建议，最小可执行步骤是什么？",
    ]
    return [f"目标：{goal}\n问题：{t}" for t in templates]


def route_agent(question: str) -> str:
    q = question.lower()
    if "风险" in question or "撤退" in question:
        return "duanban_001"
    if "证据" in question or "数据" in question:
        return "researcher_001"
    if "执行" in question or "行动" in question:
        return "writer_001"
    if "条件" in question or "判断" in question:
        return "sector_001"
    return "researcher_001"


def build_steps(goal: str) -> list[dict[str, Any]]:
    questions = split_questions(goal)
    steps: list[dict[str, Any]] = []
    for idx, q in enumerate(questions, start=1):
        steps.append(
            {
                "step": idx,
                "agent_id": route_agent(q),
                "inline_prompt": (
                    "你是子任务执行代理。仅输出结构化结论：\n"
                    "1) 结论\n2) 证据\n3) 风险\n4) 建议\n"
                    f"{q}"
                ),
                "timeout": 240,
            }
        )
    return steps
