from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class GoalStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(
                {
                    "goals": {},
                    "runs": {},
                    "methodology": {
                        "agents": {},
                        "method_variants": {
                            "baseline": {"runs": 0, "wins": 0, "score_avg": 0.0},
                            "risk_guard": {"runs": 0, "wins": 0, "score_avg": 0.0},
                            "evidence_first": {"runs": 0, "wins": 0, "score_avg": 0.0},
                        },
                    },
                    "receipts": {},
                    "experiments": [],
                }
            )

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {
                "goals": {},
                "runs": {},
                "methodology": {
                    "agents": {},
                    "method_variants": {},
                },
                "receipts": {},
                "experiments": [],
            }

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def put_goal(self, goal_id: str, payload: dict[str, Any]) -> None:
        data = self._read()
        data.setdefault("goals", {})[goal_id] = payload
        data["goals"][goal_id]["updated_at"] = self._iso()
        self._write(data)

    def get_goal(self, goal_id: str) -> dict[str, Any] | None:
        return self._read().get("goals", {}).get(goal_id)

    def list_goals(self, limit: int = 50) -> list[dict[str, Any]]:
        items = list(self._read().get("goals", {}).values())
        items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return items[:limit]

    def put_run(self, run_id: str, payload: dict[str, Any]) -> None:
        data = self._read()
        data.setdefault("runs", {})[run_id] = payload
        data["runs"][run_id]["updated_at"] = self._iso()
        self._write(data)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return self._read().get("runs", {}).get(run_id)

    def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        items = list(self._read().get("runs", {}).values())
        items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return items[:limit]

    def list_active_runs(self) -> list[dict[str, Any]]:
        items = self.list_runs(limit=1000)
        return [i for i in items if i.get("status") in {"queued", "running", "unknown"}]

    def put_receipt(self, receipt_id: str, payload: dict[str, Any]) -> None:
        data = self._read()
        data.setdefault("receipts", {})[receipt_id] = payload
        self._write(data)

    def list_receipts(self, limit: int = 100) -> list[dict[str, Any]]:
        items = list(self._read().get("receipts", {}).values())
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[:limit]

    def get_receipt(self, receipt_id: str) -> dict[str, Any] | None:
        return self._read().get("receipts", {}).get(receipt_id)

    def get_methodology(self) -> dict[str, Any]:
        return self._read().get("methodology", {"agents": {}, "method_variants": {}})

    def update_agent_weight(self, agent_id: str, delta: float, reason: str) -> None:
        data = self._read()
        agents = data.setdefault("methodology", {}).setdefault("agents", {})
        item = agents.get(agent_id) or {
            "agent_id": agent_id,
            "weight": 1.0,
            "version": 1,
            "history": [],
        }
        old = float(item.get("weight", 1.0))
        new = max(0.1, min(2.0, old + delta))
        item["weight"] = round(new, 4)
        item["version"] = int(item.get("version", 1)) + 1
        item.setdefault("history", []).append(
            {
                "at": self._iso(),
                "old_weight": old,
                "new_weight": item["weight"],
                "delta": delta,
                "reason": reason,
            }
        )
        item["updated_at"] = self._iso()
        agents[agent_id] = item
        self._write(data)

    def update_method_variant(self, method: str, score: float, win: bool) -> None:
        data = self._read()
        variants = data.setdefault("methodology", {}).setdefault("method_variants", {})
        item = variants.get(method) or {"runs": 0, "wins": 0, "score_avg": 0.0}
        old_runs = int(item.get("runs", 0))
        old_avg = float(item.get("score_avg", 0.0))
        new_runs = old_runs + 1
        new_avg = ((old_avg * old_runs) + score) / new_runs
        item["runs"] = new_runs
        item["wins"] = int(item.get("wins", 0)) + (1 if win else 0)
        item["score_avg"] = round(new_avg, 4)
        item["updated_at"] = self._iso()
        variants[method] = item
        self._write(data)

    def add_experiment(self, payload: dict[str, Any]) -> None:
        data = self._read()
        arr = data.setdefault("experiments", [])
        arr.append(payload)
        if len(arr) > 5000:
            arr = arr[-5000:]
        data["experiments"] = arr
        self._write(data)

    def list_experiments(self, limit: int = 50) -> list[dict[str, Any]]:
        arr = self._read().get("experiments", [])
        arr = sorted(arr, key=lambda x: x.get("at", ""), reverse=True)
        return arr[:limit]
