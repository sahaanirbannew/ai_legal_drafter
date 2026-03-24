from __future__ import annotations

import logging
import uuid

from agentic_app.agents.case_analysis_agent import CaseAnalysisAgent
from agentic_app.agents.drafting_agent import DraftingAgent
from agentic_app.agents.intake_agent import IntakeAgent
from agentic_app.agents.output_agent import OutputAgent
from agentic_app.agents.revision_agent import RevisionAgent
from agentic_app.agents.validation_agent import ValidationAgent
from agentic_app.models import CaseState
from agentic_app.repository import CaseRepository
from agentic_app.services import (
    AnalysisService,
    DraftingService,
    FinalizationService,
    FileStorageService,
    PdfService,
    RevisionService,
    ValidationService,
)

logger = logging.getLogger("ai_legal_drafter.agentic.orchestrator")


class CaseWorkflowOrchestrator:
    def __init__(self, repository: CaseRepository | None = None) -> None:
        self.repository = repository or CaseRepository()
        storage_service = FileStorageService(self.repository.uploads_path)
        pdf_service = PdfService()

        self.intake_agent = IntakeAgent(storage_service)
        self.analysis_agent = CaseAnalysisAgent(AnalysisService())
        self.drafting_agent = DraftingAgent(DraftingService())
        self.validation_agent = ValidationAgent(pdf_service, ValidationService())
        self.revision_agent = RevisionAgent(RevisionService())
        self.output_agent = OutputAgent(pdf_service)
        self.finalization_service = FinalizationService()

    def create_case(self) -> CaseState:
        case_state = CaseState(case_id=str(uuid.uuid4()))
        return self.repository.save(case_state)

    def get_case(self, case_id: str) -> CaseState:
        return self.repository.load(case_id)

    def ingest_upload(self, filename: str, source_file) -> CaseState:
        case_state = self.create_case()
        try:
            case_state = self.intake_agent.ingest_upload(case_state, source_file, filename)
            return self.repository.save(case_state)
        except Exception as exc:
            logger.error("Intake failed for case_id=%s: %s", case_state.case_id, exc, exc_info=True)
            case_state.status = "error"
            case_state.errors.append(str(exc))
            return self.repository.save(case_state)

    def analyze(self, case_id: str) -> CaseState:
        return self._run_agent(case_id, self.analysis_agent)

    def draft(self, case_id: str) -> CaseState:
        return self._run_agent(case_id, self.drafting_agent)

    def validate(self, case_id: str) -> CaseState:
        return self._run_agent(case_id, self.validation_agent)

    def revise(self, case_id: str) -> CaseState:
        return self._run_agent(case_id, self.revision_agent)

    def generate_outputs(self, case_id: str) -> CaseState:
        case_state = self.repository.load(case_id)
        if case_state.validation_text and not case_state.amended_draft_text:
            case_state = self._run_agent(case_id, self.revision_agent)
            if case_state.status == "error":
                return case_state
        return self._run_agent(case_id, self.output_agent)

    def finalize_and_generate(self, case_id: str, edited_text: str, comments: list[dict]) -> CaseState:
        case_state = self.repository.load(case_id)
        if not case_state.analysis:
            case_state.status = "error"
            case_state.errors.append("Case analysis not available for finalization")
            return self.repository.save(case_state)

        try:
            case_state.reviewer_comments = comments
            case_state.final_draft_text = self.finalization_service.finalize_draft(
                case_state.analysis,
                edited_text,
                case_state.validation_text,
                comments,
            )
            case_state.status = "finalized"
            self.repository.save(case_state)
            return self._run_agent(case_id, self.output_agent)
        except Exception as exc:
            logger.error("Finalization failed for case_id=%s: %s", case_id, exc, exc_info=True)
            case_state.status = "error"
            case_state.errors.append(str(exc))
            return self.repository.save(case_state)

    def _run_agent(self, case_id: str, agent) -> CaseState:
        case_state = self.repository.load(case_id)
        try:
            case_state = agent.run(case_state)
        except Exception as exc:
            logger.error("Agent %s failed for case_id=%s: %s", agent.__class__.__name__, case_id, exc, exc_info=True)
            case_state.status = "error"
            case_state.errors.append(str(exc))
        return self.repository.save(case_state)
