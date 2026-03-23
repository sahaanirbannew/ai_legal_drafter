from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from agentic_app.agents.base import BaseAgent
from agentic_app.models import CaseState
from agentic_app.services import PdfService


class OutputAgent(BaseAgent):
    def __init__(self, pdf_service: PdfService, artifacts_dir: str = "agentic_app_data/artifacts") -> None:
        self.pdf_service = pdf_service
        self.artifacts_path = Path(artifacts_dir)
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

    def run(self, case_state: CaseState) -> CaseState:
        if not case_state.draft_text:
            raise ValueError("Case draft is not available")
        final_text = case_state.final_draft_text or case_state.amended_draft_text or case_state.draft_text

        local_output = str(self.artifacts_path / f"{case_state.case_id}_output.pdf")
        self.pdf_service.create_pdf(case_state.draft_text, local_output)
        case_state.artifacts["output_pdf"] = local_output

        if case_state.final_draft_text:
            finalized_output = str(self.artifacts_path / f"{case_state.case_id}_final.pdf")
            self.pdf_service.create_pdf(case_state.final_draft_text, finalized_output)
            case_state.artifacts["final_pdf"] = finalized_output

        if case_state.amended_draft_text:
            amended_output = str(self.artifacts_path / f"{case_state.case_id}_amended.pdf")
            self.pdf_service.create_pdf(case_state.amended_draft_text, amended_output)
            case_state.artifacts["amended_pdf"] = amended_output

        if case_state.validation_text:
            validated_output = str(self.artifacts_path / f"{case_state.case_id}_validated.pdf")
            combined_text = f"{final_text}\n\nVALIDATION REPORT\n\n{case_state.validation_text}"
            self.pdf_service.create_pdf(combined_text, validated_output)
            case_state.artifacts["validated_pdf"] = validated_output

        downloads_dir = os.path.expanduser("~/Downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = self._build_base_filename(case_state.original_filename)
        if case_state.final_draft_text:
            filename = f"{base_name}_finalized_argument_{timestamp}.pdf"
        elif case_state.amended_draft_text:
            filename = f"{base_name}_amended_argument_{timestamp}.pdf"
        else:
            filename = f"{base_name}_argument_{timestamp}.pdf"
        download_path = str(Path(downloads_dir) / filename)
        self.pdf_service.create_pdf(final_text, download_path)
        case_state.artifacts["download_pdf"] = download_path
        case_state.status = "artifacts_ready"
        return case_state

    def _build_base_filename(self, original_filename: str | None) -> str:
        if not original_filename:
            return "case"
        stem = Path(original_filename).stem.lower()
        slug = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
        return slug[:80] or "case"
