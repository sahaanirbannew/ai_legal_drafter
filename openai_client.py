# OpenAI API client helper functions

import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
import json
from typing import Optional

logger = logging.getLogger('ai_legal_drafter.openai_client')

# Load environment variables from .env file
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise EnvironmentError("OPENAI_API_KEY not set in environment or .env file")

client = OpenAI(api_key=openai_api_key)


def _resolve_link_from_description(citation: dict) -> tuple[Optional[str], bool, str, str, str]:
    case_name = str(citation.get("case_name", "")).strip()
    court = str(citation.get("court", "")).strip()
    description = str(citation.get("description", "")).strip()

    description_payload = f"""{case_name}
Court: {court}
Description: {description}"""
    prompt = f"""Give me the document link (preferably link to a pdf file) for the below description:
{description_payload}

Return in json format {{ "link": < all link here >, "validated": < True if you are sure that is the file > }}
"""

    try:
        response = client.responses.create(
            model="gpt-5",
            input=prompt,
        )
        raw_response = response.output_text.strip()
        parsed = json.loads(raw_response)
        link = str(parsed.get("link", "") or "").strip()
        validated = bool(parsed.get("validated", False))
        if not link:
            return None, False, "No document link was returned by the LLM.", raw_response, prompt
        return link, validated, "Link resolved from citation description via LLM.", raw_response, prompt
    except Exception as exc:
        logger.warning("Description-based link resolution failed for %s: %s", case_name, exc)
        return None, False, "Description-based link resolution failed.", str(exc), prompt


def _ensure_required_case_fields(analysis: dict) -> dict:
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


def _sort_and_normalize_citations(citations: list[dict]) -> list[dict]:
    def court_rank(citation: dict) -> tuple[int, float]:
        court = str(citation.get("court", "")).lower()
        rank = 0 if "supreme court" in court else 1
        strength = float(citation.get("strength_score", 0) or 0)
        return (rank, -strength)

    normalized = []
    for citation in sorted(citations, key=court_rank):
        if not citation.get("case_name", "").strip():
            continue

        llm_link, llm_validated, llm_note, llm_raw_response, llm_prompt = _resolve_link_from_description(citation)
        citation["llm_link_prompt"] = llm_prompt
        citation["llm_link_response"] = llm_raw_response

        if llm_link and llm_validated:
            citation["link"] = llm_link
            citation["link_note"] = llm_note
            citation["link_verified"] = True
        else:
            citation["link"] = ""
            citation["link_note"] = llm_note if llm_link else "No validated citation link was returned by the LLM."
            citation["link_verified"] = False

        normalized.append(citation)

    return normalized


def _validate_and_refine_citations(citations: list[dict]) -> list[dict]:
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
- Do not provide Indian Kanoon search links or fallback search URLs.
- If exact document-link certainty is low, leave the link blank and mark it unverified.
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

    response = client.responses.create(
        model="gpt-5",
        input=prompt,
    )
    parsed = json.loads(response.output_text)
    return _sort_and_normalize_citations(parsed.get("citations", []))


def analyze_case(file_id):
    logger.info('analyze_case called with file_id=%s', file_id)
    try:
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
Do not invent document ids or fallback search links.
If you are unsure of the exact document URL, leave the link blank.
Do not leave applicant, defendant, or charges blank. If the document is unclear, provide the best supported extraction or inference from the text.
Do not leave forum or authority_to_approach_court blank. State the best supported legal basis from the document, such as the section invoked, the revisional/appellate/writ jurisdiction, or the procedural route used to approach the court.
Frame the arguments from the applicant's side as strongly as the record and law reasonably permit.
Interpret the statutory provisions, procedural safeguards, and cited precedents in a way that most strongly supports the applicant, while remaining legally defensible.
Prefer arguments that show lack of ingredients of the offence, non-application of mind, procedural illegality, weak mens rea, weak nexus, overreach by the lower court, and any other ground that weakens the prosecution case where applicable.
Think like experienced Supreme Court counsel: identify the strongest defensible legal route, give the applicant the benefit of every fairly arguable interpretation, and organise the case around the most persuasive legal propositions first.
Do not leave plan_of_action blank. State clearly whether the next step should be a fresh petition or a revised petition, what precise remedy should be sought, and why that is the best course in this matter.
"""

        response = client.responses.create(
            model="gpt-5",
            input=[{
                "role":"user",
                "content":[
                    {"type":"input_file","file_id":file_id},
                    {"type":"input_text","text":prompt}
                ]
            }]
        )

        logger.debug('analyze_case OpenAI response: %s', response)
        analysis = _ensure_required_case_fields(json.loads(response.output_text))
        analysis["citations"] = _validate_and_refine_citations(analysis.get("citations", []))
        return analysis
    except Exception as e:
        logger.error('analyze_case failed: %s', e, exc_info=True)
        raise
