from __future__ import annotations

from agentic_app.agents.base import BaseAgent
from agentic_app.models import CaseState
from agentic_app.services import RevisionService


class RevisionAgent(BaseAgent):
    def __init__(self, revision_service: RevisionService) -> None:
        self.revision_service = revision_service

    def run(self, case_state: CaseState) -> CaseState:
        if not case_state.analysis or not case_state.draft_text:
            raise ValueError("Case is not ready for revision")
        if not case_state.validation_text:
            raise ValueError("Validation report is required before revision")

        case_state.amended_draft_text = self.revision_service.revise_draft(
            case_state.analysis,
            case_state.draft_text,
            case_state.validation_text,
        )
        case_state.status = "amended"
        return case_state
