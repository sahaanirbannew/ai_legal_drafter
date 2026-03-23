from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CaseState:
    case_id: str
    status: str = "created"
    uploaded_pdf_path: str | None = None
    original_filename: str | None = None
    openai_file_id: str | None = None
    analysis: dict[str, Any] | None = None
    draft_text: str | None = None
    validation_text: str | None = None
    validation_data: dict[str, Any] | None = None
    amended_draft_text: str | None = None
    final_draft_text: str | None = None
    reviewer_comments: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaseState":
        return cls(**data)
