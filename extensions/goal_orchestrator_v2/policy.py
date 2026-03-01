from __future__ import annotations

import random
from typing import Any

METHODS = ["baseline", "risk_guard", "evidence_first"]


def _score(m: dict[str, Any]) -> float:
    runs = int(m.get("runs", 0))
    wins = int(m.get("wins", 0))
    if runs <= 0:
        return 0.5
    return wins / runs


def choose_method(methodology: dict[str, Any], epsilon: float) -> str:
    variants = methodology.get("method_variants", {})
    if random.random() < max(0.0, min(1.0, epsilon)):
        return random.choice(METHODS)

    best = "baseline"
    best_score = -1.0
    for m in METHODS:
        info = variants.get(m, {})
        s = _score(info)
        if s > best_score:
            best = m
            best_score = s
    return best


def evaluate_outcome(run: dict[str, Any]) -> tuple[int, int, float]:
    steps = run.get("task_steps") or []
    ok = len([s for s in steps if s.get("status") == "completed"])
    bad = len([s for s in steps if s.get("status") in {"failed", "timeout", "cancelled"}])
    total = max(1, len(steps))
    score = (ok - bad) / total
    return ok, bad, score
