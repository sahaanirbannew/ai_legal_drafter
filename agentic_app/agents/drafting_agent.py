from __future__ import annotations

from agentic_app.agents.base import BaseAgent
from agentic_app.models import CaseState
from agentic_app.services import DraftingService


class DraftingAgent(BaseAgent):
    def __init__(self, drafting_service: DraftingService) -> None:
        self.drafting_service = drafting_service

    def run(self, case_state: CaseState) -> CaseState:
        if not case_state.analysis:
            raise ValueError("Case analysis not available")
        case_state.draft_text = self.drafting_service.build_draft(case_state.analysis)
        case_state.status = "drafted"
        return case_state

