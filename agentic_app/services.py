from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from gemini_validator import validate_case
from openai_client import analyze_case
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


class OpenAIFileService:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file or environment variables.")
        self.client = OpenAI(api_key=api_key)

    def upload_file(self, path: str) -> str:
        uploaded = self.client.files.create(file=open(path, "rb"), purpose="assistants")
        return uploaded.id


class AnalysisService:
    def analyze(self, openai_file_id: str) -> dict:
        return analyze_case(openai_file_id)


class DraftingService:
    def build_draft(self, analysis: dict) -> str:
        return build_argument(analysis)


class RevisionService:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file or environment variables.")
        self.client = OpenAI(api_key=api_key)

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

        response = self.client.responses.create(
            model="gpt-5",
            input=prompt,
        )
        return response.output_text.strip()


class FinalizationService:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file or environment variables.")
        self.client = OpenAI(api_key=api_key)

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
        response = self.client.responses.create(
            model="gpt-5",
            input=prompt,
        )
        return response.output_text.strip()


class ValidationService:
    def validate(self, original_pdf_path: str, draft_pdf_path: str, analysis: dict) -> tuple[str, dict]:
        validation_text = validate_case(original_pdf_path, draft_pdf_path, analysis)
        try:
            validation_data = json.loads(validation_text)
        except json.JSONDecodeError:
            logger.warning("Validation response was not valid JSON")
            validation_data = {
                "raw_text": validation_text,
                "issues_found": [],
                "suggested_improvements": [],
                "hallucinated_citations": [],
            }
        return validation_text, validation_data


class PdfService:
    def create_pdf(self, text: str, path: str) -> str:
        create_pdf(text, path)
        return path
