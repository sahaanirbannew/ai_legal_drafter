# OpenAI API client helper functions

import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
import json
from urllib.parse import quote_plus

logger = logging.getLogger('ai_legal_drafter.openai_client')

# Load environment variables from .env file
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise EnvironmentError("OPENAI_API_KEY not set in environment or .env file")

client = OpenAI(api_key=openai_api_key)


def _build_indiankanoon_search_link(case_name: str) -> str:
    return f"https://indiankanoon.org/search/?formInput={quote_plus(case_name)}"


def _sort_and_normalize_citations(citations: list[dict]) -> list[dict]:
    def court_rank(citation: dict) -> tuple[int, float]:
        court = str(citation.get("court", "")).lower()
        rank = 0 if "supreme court" in court else 1
        strength = float(citation.get("strength_score", 0) or 0)
        return (rank, -strength)

    normalized = []
    for citation in sorted(citations, key=court_rank):
        case_name = citation.get("case_name", "").strip()
        if not case_name:
            continue

        link = str(citation.get("link", "") or "").strip()
        link_verified = bool(citation.get("link_verified", False))

        # Prefer safe search links unless the model explicitly says the direct link is verified.
        if not link or ("indiankanoon.org/doc/" in link and not link_verified):
            citation["link"] = _build_indiankanoon_search_link(case_name)
            citation["link_note"] = citation.get(
                "link_note",
                "Search link provided because an exact court-consistent document URL was not confidently verified.",
            )
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
- When exact document-link certainty is low, provide an Indian Kanoon search URL using the exact case name.
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
You are a senior Indian constitutional lawyer.

Analyse the uploaded legal document and respond ONLY in JSON.

Tasks:
1. Identify the applicant's demands.
2. Suggest better legal arguments to strengthen the applicant's case.
3. Suggest if "Non-application of mind" can be argued.
4. Find relevant Supreme Court or High Court citations.

Return JSON format:

{
 "demands": [],
 "arguments": [],
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
Do not invent Indian Kanoon document ids.
If you are unsure of the exact document URL, provide an Indian Kanoon search URL for the exact case name instead of a direct document link.
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
        analysis = json.loads(response.output_text)
        analysis["citations"] = _validate_and_refine_citations(analysis.get("citations", []))
        return analysis
    except Exception as e:
        logger.error('analyze_case failed: %s', e, exc_info=True)
        raise
