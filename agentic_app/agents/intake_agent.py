from __future__ import annotations

from agentic_app.agents.base import BaseAgent
from agentic_app.models import CaseState
from agentic_app.services import FileStorageService


class IntakeAgent(BaseAgent):
    def __init__(self, storage_service: FileStorageService) -> None:
        self.storage_service = storage_service

    def run(self, case_state: CaseState) -> CaseState:
        raise NotImplementedError("Use ingest_upload for intake agent")

    def ingest_upload(self, case_state: CaseState, source_file, filename: str) -> CaseState:
        uploaded_pdf_path = self.storage_service.save_upload(source_file, filename, case_state.case_id)

        case_state.uploaded_pdf_path = uploaded_pdf_path
        case_state.original_filename = filename
        case_state.status = "uploaded"
        return case_state
