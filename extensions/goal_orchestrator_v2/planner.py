from __future__ import annotations

from typing import Any

METHOD_TEMPLATES = {
    "baseline": "请给出结构化结论：结论/证据/风险/建议。",
    "risk_guard": "请优先识别风险、失效条件、撤退触发点，再给行动建议。",
    "evidence_first": "请优先列出证据链与反证，再给保守建议。",
}


QUESTIONS = [
    "这个目标的核心判断条件是什么？",
    "当前最支持和最反对该目标的证据是什么？",
    "执行该目标的风险与失效条件是什么？",
    "今天最小可执行步骤是什么？",
]


def route_agent(question: str) -> str:
    if "风险" in question or "失效" in question:
        return "duanban_001"
    if "证据" in question or "反对" in question:
        return "researcher_001"
    if "执行" in question or "步骤" in question:
        return "writer_001"
    return "sector_001"


def build_steps(goal: str, method: str) -> list[dict[str, Any]]:
    method_hint = METHOD_TEMPLATES.get(method, METHOD_TEMPLATES["baseline"])
    steps: list[dict[str, Any]] = []
    for idx, q in enumerate(QUESTIONS, start=1):
        prompt = (
            "你是子任务执行代理。仅输出结构化结论。\n"
            f"方法论约束：{method_hint}\n"
            f"目标：{goal}\n"
            f"问题：{q}"
        )
        steps.append(
            {
                "step": idx,
                "agent_id": route_agent(q),
                "inline_prompt": prompt,
                "timeout": 300,
            }
        )
    return steps


def build_replan_steps(goal: str, method: str, prev_run: dict[str, Any]) -> list[dict[str, Any]]:
    failed_steps = [s for s in (prev_run.get("task_steps") or []) if s.get("status") in {"failed", "timeout"}]
    if not failed_steps:
        return build_steps(goal, method)

    method_hint = METHOD_TEMPLATES.get(method, METHOD_TEMPLATES["baseline"])
    steps: list[dict[str, Any]] = []
    for idx, s in enumerate(failed_steps, start=1):
        question = f"重规划修复：step={s.get('step')} agent={s.get('agent_id')} 的失败原因与替代路径是什么？"
        steps.append(
            {
                "step": idx,
                "agent_id": s.get("agent_id") or "researcher_001",
                "inline_prompt": (
                    "你是重规划修复代理。\n"
                    f"方法论约束：{method_hint}\n"
                    f"目标：{goal}\n"
                    f"问题：{question}"
                ),
                "timeout": 300,
            }
        )
    return steps
