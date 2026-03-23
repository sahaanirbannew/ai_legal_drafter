from __future__ import annotations

import json
from pathlib import Path

from .models import CaseState


class CaseRepository:
    def __init__(self, base_dir: str = "agentic_app_data") -> None:
        self.base_path = Path(base_dir)
        self.cases_path = self.base_path / "cases"
        self.uploads_path = self.base_path / "uploads"
        self.cases_path.mkdir(parents=True, exist_ok=True)
        self.uploads_path.mkdir(parents=True, exist_ok=True)

    def case_path(self, case_id: str) -> Path:
        return self.cases_path / f"{case_id}.json"

    def save(self, case_state: CaseState) -> CaseState:
        self.case_path(case_state.case_id).write_text(
            json.dumps(case_state.to_dict(), indent=2),
            encoding="utf-8",
        )
        return case_state

    def load(self, case_id: str) -> CaseState:
        path = self.case_path(case_id)
        if not path.exists():
            raise FileNotFoundError(f"Case {case_id} not found")
        return CaseState.from_dict(json.loads(path.read_text(encoding="utf-8")))

