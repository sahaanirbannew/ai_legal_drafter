from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path

from dotenv import load_dotenv

from gemini_client import analyze_case, generate_text, summarize_argument_differences
from gemini_validator import validate_case
from pdf_generator import create_pdf
from prompt import build_argument

logger = logging.getLogger("ai_legal_drafter.agentic.services")

load_dotenv()


class FileStorageService:
    def __init__(self, uploads_dir: Path) -> None:
        self.uploads_dir = uploads_dir
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, source_file, filename: str, case_id: str) -> str:
        safe_name = Path(filename).name
        path = self.uploads_dir / f"{case_id}_{safe_name}"
        with open(path, "wb") as buffer:
            shutil.copyfileobj(source_file, buffer)
        return str(path)


class AnalysisService:
    def analyze(self, pdf_path: str) -> dict:
        return analyze_case(pdf_path)


class DraftingService:
    def build_draft(self, analysis: dict) -> str:
        return build_argument(analysis)

    def build_argument_differences(self, analysis: dict, draft_text: str) -> list[str]:
        return summarize_argument_differences(analysis, draft_text)


class RevisionService:
    def revise_draft(self, analysis: dict, draft_text: str, validation_text: str) -> str:
        prompt = f"""
You are senior Supreme Court counsel in India revising a draft legal argument for the applicant.

You will receive:
1. Case analysis JSON
2. Existing legal draft
3. Validation report

Your job:
- Rewrite the draft so it addresses the validator's criticisms.
- Remove or soften weak, unsupported, or hallucinated points.
- Improve the structure and legal reasoning.
- Use easy legalese. Avoid unnecessarily difficult, archaic, or ornamental wording.
- Stay close to the style, tone, and vocabulary used in the input case document wherever possible.
- Clearly state why this court/forum is being approached and under what legal authority, provision, or jurisdiction the filing is maintainable.
- Include a separate section labelled exactly "Plan of Action:".
- In that section, state whether the next step should be a new petition or a revised petition.
- State the most appropriate remedy to be sought in this particular case.
- Give reasons for that choice, preferably linking the recommendation to the cited authorities and procedural posture.
- Interpret the law firmly in favour of the applicant wherever that interpretation is reasonably open on the record and authorities.
- Present the strongest defensible reading of the statute, precedent, and procedural safeguards for the applicant's case.
- Where two readings are possible, prefer the one that better supports discharge, quashing, interference, or other relief sought by the applicant, provided it is legally arguable.
- Think and write like experienced Supreme Court counsel: lead with the strongest legal propositions, state the applicant-friendly interpretation confidently, and press every sustainable legal advantage available on the record.
- Consider humanitarian grounds, mental health considerations, and the spirit of the law, but only if they are genuinely supportable from the case materials or reasonable legal inferences.
- Do not force those themes if they are not applicable.
- Preserve a professional court-ready tone.
- Keep citations grounded in the analysis provided.

Return only the amended legal argument in plain text.

CASE ANALYSIS JSON:
{json.dumps(analysis, ensure_ascii=True, indent=2)}

EXISTING DRAFT:
{draft_text}

VALIDATION REPORT:
{validation_text}
"""
        return generate_text(prompt)


class FinalizationService:
    def finalize_draft(
        self,
        analysis: dict,
        edited_text: str,
        validation_text: str | None,
        comments: list[dict],
    ) -> str:
        prompt = f"""
You are senior Supreme Court counsel in India finalising a draft legal argument for filing on behalf of the applicant.

You will receive:
1. Case analysis JSON
2. The user's currently edited draft text
3. The validation report, if any
4. Reviewer comments tied to selected parts of the draft

Your job:
- Produce the final polished legal argument in plain text.
- Respect the user's manual edits unless they create a clear legal, structural, or logical problem.
- Incorporate reviewer comments where appropriate.
- Use easy legalese. Avoid unnecessarily difficult or obscure wording.
- Keep the language close to the wording and style used in the source case papers where that can be done cleanly.
- Clearly justify why the matter is before this court and under what legal authority, section, or jurisdiction the court is being approached.
- Include a separate section labelled exactly "Plan of Action:".
- In that section, state whether this matter should proceed by a new petition or a revised petition.
- State the most appropriate remedy to seek in this case.
- Give reasons for that course, preferably supported by the cited authorities and the procedural posture on record.
- Interpret the law strongly in favour of the applicant, so long as the interpretation remains grounded in the record and the cited authorities.
- Present the strongest legally defensible construction of the facts, statutory provisions, and precedents for obtaining the relief sought.
- Do not dilute the argument unnecessarily. If a strong legal point is fairly available, articulate it clearly and with confidence.
- Think and write like experienced Supreme Court counsel: structure the submission around the best legal grounds first, use authority strategically, and press the most persuasive applicant-friendly interpretation that the materials can sustain.
- Where appropriate, strengthen the argument using humanitarian grounds, mental health considerations, and the spirit of the law, but only if supportable from the materials.
- Retain or improve citation references and keep them grounded in the provided analysis.
- Do not output notes, markdown fences, explanations, or a changelog.

CASE ANALYSIS JSON:
{json.dumps(analysis, ensure_ascii=True, indent=2)}

USER-EDITED DRAFT:
{edited_text}

VALIDATION REPORT:
{validation_text or "No validation report provided."}

REVIEWER COMMENTS:
{json.dumps(comments, ensure_ascii=True, indent=2)}
"""
        return generate_text(prompt)


class ValidationService:
    @staticmethod
    def _extract_json_payload(text: str) -> dict:
        text = str(text or "").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    @staticmethod
    def _fallback_validation_data(validation_text: str, reason: str) -> dict:
        return {
            "validation_failed": True,
            "failure_reason": reason,
            "raw_text": validation_text,
            "overall_validity_score": None,
            "logic_score": None,
            "citation_validity_score": None,
            "issues_found": [reason] if reason else [],
            "suggested_improvements": [
                "Retry validation after checking Gemini API availability, PDF readability, and response format."
            ],
            "hallucinated_citations": [],
        }

    def validate(self, original_pdf_path: str, draft_pdf_path: str, analysis: dict) -> tuple[str, dict]:
        validation_text = validate_case(original_pdf_path, draft_pdf_path, analysis)
        try:
            validation_data = self._extract_json_payload(validation_text)
            validation_data.setdefault("validation_failed", False)
            validation_data.setdefault("failure_reason", "")
            validation_data.setdefault("issues_found", [])
            validation_data.setdefault("suggested_improvements", [])
            validation_data.setdefault("hallucinated_citations", [])
        except Exception as exc:
            logger.warning("Validation response was not valid JSON: %s", exc)
            validation_data = self._fallback_validation_data(
                validation_text,
                f"Gemini returned a response that could not be parsed as JSON: {exc}",
            )
        return validation_text, validation_data


class PdfService:
    def create_pdf(self, text: str, path: str) -> str:
        create_pdf(text, path)
        return path
