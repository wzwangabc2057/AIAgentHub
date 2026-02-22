from __future__ import annotations

import json
import urllib.request
from typing import Any


class AIAgentClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get(self, path: str, timeout: int = 30) -> dict[str, Any]:
        req = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def create_chain(self, name: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post("/api/chains", {"name": name, "steps": steps}, timeout=60)

    def get_chain(self, chain_id: str) -> dict[str, Any]:
        return self._get(f"/api/chains/{chain_id}", timeout=30)
