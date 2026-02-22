import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class GoalStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"goals": {}, "runs": {}, "methodology": {"agents": {}}, "receipts": {}})

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"goals": {}, "runs": {}, "methodology": {"agents": {}}, "receipts": {}}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def put_goal(self, goal_id: str, payload: dict[str, Any]) -> None:
        data = self._read()
        data.setdefault("goals", {})[goal_id] = payload
        data["goals"][goal_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write(data)

    def get_goal(self, goal_id: str) -> dict[str, Any] | None:
        data = self._read()
        return data.get("goals", {}).get(goal_id)

    def list_goals(self, limit: int = 50) -> list[dict[str, Any]]:
        data = self._read()
        values = list(data.get("goals", {}).values())
        values.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return values[:limit]

    def put_run(self, run_id: str, payload: dict[str, Any]) -> None:
        data = self._read()
        data.setdefault("runs", {})[run_id] = payload
        data["runs"][run_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write(data)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        data = self._read()
        return data.get("runs", {}).get(run_id)

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        data = self._read()
        values = list(data.get("runs", {}).values())
        values.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return values[:limit]

    def update_methodology_weight(self, agent_id: str, delta: float, reason: str) -> None:
        data = self._read()
        agents = data.setdefault("methodology", {}).setdefault("agents", {})
        item = agents.get(agent_id) or {
            "agent_id": agent_id,
            "weight": 1.0,
            "version": 1,
            "history": [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        old = float(item.get("weight", 1.0))
        new = max(0.1, min(2.0, old + delta))
        item["weight"] = round(new, 4)
        item["version"] = int(item.get("version", 1)) + 1
        item.setdefault("history", []).append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "old_weight": old,
                "new_weight": item["weight"],
                "delta": delta,
                "reason": reason,
            }
        )
        item["updated_at"] = datetime.now(timezone.utc).isoformat()
        agents[agent_id] = item
        self._write(data)

    def get_methodology(self) -> dict[str, Any]:
        data = self._read()
        return data.get("methodology", {"agents": {}})

    def put_receipt(self, receipt_id: str, payload: dict[str, Any]) -> None:
        data = self._read()
        data.setdefault("receipts", {})[receipt_id] = payload
        self._write(data)

    def get_receipt(self, receipt_id: str) -> dict[str, Any] | None:
        data = self._read()
        return data.get("receipts", {}).get(receipt_id)

    def list_receipts(self, limit: int = 100) -> list[dict[str, Any]]:
        data = self._read()
        values = list(data.get("receipts", {}).values())
        values.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return values[:limit]
