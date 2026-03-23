from __future__ import annotations

from pathlib import Path

from agentic_app.agents.base import BaseAgent
from agentic_app.models import CaseState
from agentic_app.services import PdfService, ValidationService


class ValidationAgent(BaseAgent):
    def __init__(self, pdf_service: PdfService, validation_service: ValidationService, artifacts_dir: str = "agentic_app_data/artifacts") -> None:
        self.pdf_service = pdf_service
        self.validation_service = validation_service
        self.artifacts_path = Path(artifacts_dir)
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

    def run(self, case_state: CaseState) -> CaseState:
        if not case_state.uploaded_pdf_path or not case_state.analysis or not case_state.draft_text:
            raise ValueError("Case is not ready for validation")

        draft_pdf_path = str(self.artifacts_path / f"{case_state.case_id}_draft.pdf")
        self.pdf_service.create_pdf(case_state.draft_text, draft_pdf_path)

        validation_text, validation_data = self.validation_service.validate(
            case_state.uploaded_pdf_path,
            draft_pdf_path,
            case_state.analysis,
        )

        case_state.validation_text = validation_text
        case_state.validation_data = validation_data
        case_state.artifacts["draft_pdf"] = draft_pdf_path
        case_state.status = "validated"
        return case_state

