from __future__ import annotations

from agentic_app.agents.base import BaseAgent
from agentic_app.models import CaseState
from agentic_app.services import AnalysisService


class CaseAnalysisAgent(BaseAgent):
    def __init__(self, analysis_service: AnalysisService) -> None:
        self.analysis_service = analysis_service

    def run(self, case_state: CaseState) -> CaseState:
        if not case_state.uploaded_pdf_path:
            raise ValueError("Case is missing uploaded PDF path")
        case_state.analysis = self.analysis_service.analyze(case_state.uploaded_pdf_path)
        case_state.status = "analyzed"
        return case_state
