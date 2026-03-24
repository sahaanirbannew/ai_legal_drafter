from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

from dotenv import load_dotenv
import google.generativeai as genai

logger = logging.getLogger("ai_legal_drafter.gemini_client")

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise EnvironmentError("GEMINI_API_KEY not set in environment or .env file")

genai.configure(api_key=gemini_api_key)

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
model = genai.GenerativeModel(MODEL_NAME)


def _extract_json_payload(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _generate_content(prompt: str, parts: list[dict[str, Any]] | None = None, expect_json: bool = False) -> str:
    payload: list[Any] = [prompt]
    if parts:
        payload.extend(parts)

    generation_config = {"response_mime_type": "application/json"} if expect_json else None
    response = model.generate_content(payload, generation_config=generation_config)
    return response.text.strip()


def generate_text(prompt: str, parts: list[dict[str, Any]] | None = None) -> str:
    return _generate_content(prompt, parts=parts, expect_json=False)


def generate_json(prompt: str, parts: list[dict[str, Any]] | None = None) -> tuple[dict[str, Any], str]:
    raw_text = _generate_content(prompt, parts=parts, expect_json=True)
    return _extract_json_payload(raw_text), raw_text


def _read_pdf_part(path: str) -> dict[str, Any]:
    with open(path, "rb") as file_obj:
        return {"mime_type": "application/pdf", "data": file_obj.read()}


def _resolve_link_from_description(citation: dict) -> tuple[Optional[str], bool, str, str, str]:
    case_name = str(citation.get("case_name", "")).strip()
    court = str(citation.get("court", "")).strip()
    description = str(citation.get("description", "")).strip()

    description_payload = f"""{case_name}
Court: {court}
Description: {description}"""
    prompt = f"""
Give me the PDF link from Supreme Court or High Court of India for the case given at the end of the instructions.

Mandatory response format:
{{
"link": < all link here >,
"validated": {{
  "is_SupremeCourt": <True if the source is Supreme Court of India website>,
  "is_HighCourt": <True if the source is High Court of India website>,
  "is_PDF": <True if the link is PDF file>,
  "is_Correct": <True if the file content matches description>
}}
}}

Case:
{description_payload}
"""

    try:
        parsed, raw_response = generate_json(prompt)
        link = str(parsed.get("link", "") or "").strip()
        validation = parsed.get("validated", {}) or {}
        is_supreme = bool(validation.get("is_SupremeCourt", False))
        is_high = bool(validation.get("is_HighCourt", False))
        is_pdf = bool(validation.get("is_PDF", False))
        is_correct = bool(validation.get("is_Correct", False))
        validated = bool(link) and is_pdf and is_correct and (is_supreme or is_high)
        if not link:
            return None, False, "No document link was returned by Gemini.", raw_response, prompt
        if validated:
            return link, True, "Link resolved from citation description via Gemini.", raw_response, prompt
        return link, False, "Gemini returned a link, but the validation flags did not fully confirm it.", raw_response, prompt
    except Exception as exc:
        logger.warning("Description-based link resolution failed for %s: %s", case_name, exc)
        return None, False, "Description-based link resolution failed.", str(exc), prompt


def _ensure_required_case_fields(analysis: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "applicant": "Not clearly named in the extracted materials.",
        "defendant": "Not clearly named in the extracted materials.",
        "forum": "Appropriate court/forum to be stated from the case papers.",
        "authority_to_approach_court": "Jurisdictional basis to be stated from the case papers.",
        "charges": ["Not clearly identified from the extracted materials."],
        "demands": ["No demand extracted."],
        "arguments": [],
        "plan_of_action": {
            "filing_recommendation": "State whether this should proceed as a fresh petition or revised petition.",
            "recommended_remedy": "State the principal relief that should be sought.",
            "reasons": ["State the legal and factual reasons for that course."],
        },
        "citations": [],
    }
    for key, default_value in defaults.items():
        if key not in analysis or analysis[key] in (None, "", []):
            analysis[key] = default_value
    return analysis


def _sort_and_normalize_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def court_rank(citation: dict[str, Any]) -> tuple[int, float]:
        court = str(citation.get("court", "")).lower()
        rank = 0 if "supreme court" in court else 1
        strength = float(citation.get("strength_score", 0) or 0)
        return (rank, -strength)

    normalized: list[dict[str, Any]] = []
    for citation in sorted(citations, key=court_rank):
        if not str(citation.get("case_name", "")).strip():
            continue

        llm_link, llm_validated, llm_note, llm_raw_response, llm_prompt = _resolve_link_from_description(citation)
        citation["llm_link_prompt"] = llm_prompt
        citation["llm_link_response"] = llm_raw_response
        try:
            citation["llm_link_validation"] = _extract_json_payload(llm_raw_response).get("validated", {})
        except Exception:
            citation["llm_link_validation"] = {}

        if llm_link and llm_validated:
            citation["link"] = llm_link
            citation["link_note"] = llm_note
            citation["link_verified"] = True
        else:
            citation["link"] = llm_link or ""
            citation["link_note"] = llm_note if llm_link else "No validated citation link was returned by Gemini."
            citation["link_verified"] = False

        normalized.append(citation)

    return normalized


def _validate_and_refine_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not citations:
        return []

    prompt = f"""
You are validating legal citations for an Indian criminal-law drafting system.

You will receive a list of candidate citations. Clean and refine them.

Rules:
- Keep only real and relevant citations.
- Strongly prefer Supreme Court of India authorities.
- Use High Court authorities only when especially relevant and when Supreme Court authority is insufficient.
- Ensure the case name and court are consistent.
- If you are not highly confident about an exact direct document URL, do NOT invent a direct link.
- Leave the link blank if exact document-link certainty is low.
- Return no more than 5 citations.

Return ONLY valid JSON with this format:
{{
  "citations": [
    {{
      "case_name": "",
      "court": "",
      "description": "",
      "why_cited": "",
      "relevance_to_case": "",
      "strengthens_case": "",
      "relevance_score": 0,
      "strength_score": 0,
      "link": "",
      "link_verified": false,
      "link_note": ""
    }}
  ]
}}

Candidate citations:
{json.dumps(citations, ensure_ascii=True, indent=2)}
"""

    parsed, _ = generate_json(prompt)
    return _sort_and_normalize_citations(parsed.get("citations", []))


def analyze_case(pdf_path: str) -> dict[str, Any]:
    logger.info("analyze_case called with pdf_path=%s", pdf_path)
    prompt = """
You are a senior Supreme Court lawyer in India representing the applicant.

Analyse the uploaded legal document and respond ONLY in JSON.

Tasks:
1. Identify the applicant.
2. Identify the defendant/respondent.
3. Identify the court/forum being approached in the document.
4. Identify under what legal authority, provision, jurisdiction, or procedural route the applicant has come to that court.
5. Identify the charges/offences involved.
6. Identify the applicant's demands.
7. Suggest better legal arguments to strengthen the applicant's case.
8. Suggest if "Non-application of mind" can be argued.
9. State a clear plan of action: whether this should proceed as a new petition or a revised petition.
10. State the most appropriate remedy to be sought in this case.
11. Give reasons for that procedural and remedial choice, preferably supported by the cited authorities.
12. Find relevant Supreme Court or High Court citations.

Return JSON format:

{
 "applicant": "",
 "defendant": "",
 "forum": "",
 "authority_to_approach_court": "",
 "charges": [],
 "demands": [],
 "arguments": [],
 "plan_of_action": {
   "filing_recommendation": "",
   "recommended_remedy": "",
   "reasons": []
 },
 "citations":[
  {
   "case_name":"",
   "court":"",
   "description":"",
   "why_cited":"",
   "relevance_to_case":"",
   "strengthens_case":"",
   "relevance_score":0,
   "strength_score":0,
   "link":"",
   "link_verified": false,
   "link_note":""
  }
 ]
}

IMPORTANT:
Only cite real cases.
Strongly prefer Supreme Court of India cases.
Use High Court cases sparingly and only when they are uniquely relevant.
If you are unsure of the exact document URL, leave the link blank.
Do not leave applicant, defendant, or charges blank. If the document is unclear, provide the best supported extraction or inference from the text.
Do not leave forum or authority_to_approach_court blank. State the best supported legal basis from the document, such as the section invoked, the revisional/appellate/writ jurisdiction, or the procedural route used to approach the court.
Frame the arguments from the applicant's side as strongly as the record and law reasonably permit.
Interpret the statutory provisions, procedural safeguards, and cited precedents in a way that most strongly supports the applicant, while remaining legally defensible.
Prefer arguments that show lack of ingredients of the offence, non-application of mind, procedural illegality, weak mens rea, weak nexus, overreach by the lower court, and any other ground that weakens the prosecution case where applicable.
Think like experienced Supreme Court counsel: identify the strongest defensible legal route, give the applicant the benefit of every fairly arguable interpretation, and organise the case around the most persuasive legal propositions first.
Do not leave plan_of_action blank. State clearly whether the next step should be a fresh petition or a revised petition, what precise remedy should be sought, and why that is the best course in this matter.
"""

    parsed, raw_response = generate_json(prompt, parts=[_read_pdf_part(pdf_path)])
    logger.debug("analyze_case Gemini response: %s", raw_response)
    analysis = _ensure_required_case_fields(parsed)
    analysis["citations"] = _validate_and_refine_citations(analysis.get("citations", []))
    return analysis


def summarize_argument_differences(analysis: dict[str, Any], draft_text: str) -> list[str]:
    prompt = f"""
You are a senior Indian lawyer comparing:
1. the existing case-side argument points extracted from the source material, and
2. the proposed drafted argument prepared for filing.

Write only JSON in this format:
{{
  "bullets": [
    ""
  ]
}}

Instructions:
- Explain the differences from a lawyer's point of view.
- Use short bullet points.
- Focus on legal structure, maintainability/jurisdiction, remedy framing, strength of authorities, factual linkage, and persuasive force.
- Do not praise generally. Be concrete.
- Return 4 to 6 bullets.

EXISTING CASE ARGUMENT POINTS:
{json.dumps(analysis.get("arguments", []), ensure_ascii=True, indent=2)}

CASE DEMANDS:
{json.dumps(analysis.get("demands", []), ensure_ascii=True, indent=2)}

PROPOSED DRAFT:
{draft_text}
"""
    try:
        parsed, _ = generate_json(prompt)
        bullets = parsed.get("bullets", [])
        if isinstance(bullets, list) and bullets:
            return [str(item).strip() for item in bullets if str(item).strip()]
    except Exception as exc:
        logger.warning("Argument-difference summary generation failed: %s", exc)

    fallback = []
    if analysis.get("authority_to_approach_court"):
        fallback.append("The proposed draft expressly states jurisdiction and the legal basis for approaching the court, which is often missing or only implicit in raw case-side argument notes.")
    if analysis.get("citations"):
        fallback.append("The proposed draft is more authority-driven and ties the case theory to identified precedent instead of leaving the legal position as bare assertion.")
    if analysis.get("plan_of_action"):
        fallback.append("The proposed draft is more remedially precise because it states what filing route and relief should be pursued, rather than only listing grievances.")
    fallback.append("The proposed draft is more structured for adjudication because it converts scattered argument points into a filing-ready sequence of jurisdiction, demands, legal grounds, and relief.")
    return fallback[:4]
