from __future__ import annotations

import json
from pathlib import Path


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text('{"jobs": {}}', encoding="utf-8")

    def load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def mark_job(self, source_job_id: str, status: str, payload: dict | None = None) -> None:
        state = self.load()
        jobs = state.setdefault("jobs", {})
        jobs[source_job_id] = {"status": status, **(payload or {})}
        self.save(state)

    def get_job_status(self, source_job_id: str) -> str | None:
        state = self.load()
        item = state.get("jobs", {}).get(source_job_id)
        if not item:
            return None
        return item.get("status")
