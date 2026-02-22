import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class GoalStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"goals": {}})

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"goals": {}}

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
