# OpenAI API client helper functions

import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
import json
import re
import urllib.request
from urllib.parse import quote_plus

logger = logging.getLogger('ai_legal_drafter.openai_client')

# Load environment variables from .env file
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise EnvironmentError("OPENAI_API_KEY not set in environment or .env file")

client = OpenAI(api_key=openai_api_key)


def _build_indiankanoon_search_link(case_name: str) -> str:
    return f"https://indiankanoon.org/search/?formInput={quote_plus('ruling + ' + case_name)}"


def _normalise_case_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _case_match_score(expected_case_name: str, candidate_title: str) -> int:
    expected = _normalise_case_text(expected_case_name)
    candidate = _normalise_case_text(candidate_title)
    if not expected or not candidate:
        return 0

    expected_tokens = {token for token in expected.split() if len(token) > 2}
    candidate_tokens = set(candidate.split())
    overlap = expected_tokens & candidate_tokens
    score = len(overlap)

    if expected in candidate:
        score += 100

    return score


def _fetch_resolved_indiankanoon_doc_link(case_name: str) -> tuple[str, bool, str]:
    search_link = _build_indiankanoon_search_link(case_name)
    request = urllib.request.Request(search_link, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        logger.warning("Indian Kanoon resolution failed for %s: %s", case_name, exc)
        return search_link, False, "Search link provided because the Indian Kanoon result page could not be resolved."

    candidates = re.findall(r'<a[^>]+href="(/doc/\d+/)"[^>]*>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL)
    ranked_candidates = []
    for href, anchor_html in candidates:
        title = re.sub(r"<[^>]+>", " ", anchor_html)
        title = re.sub(r"\s+", " ", title).strip()
        score = _case_match_score(case_name, title)
        if score > 0:
            ranked_candidates.append((score, href, title))

    if not ranked_candidates:
        return search_link, False, "Search link provided because no direct Indian Kanoon document result was found."

    ranked_candidates.sort(key=lambda item: item[0], reverse=True)
    _, best_href, best_title = ranked_candidates[0]

    return (
        f"https://indiankanoon.org{best_href}",
        True,
        f"Direct Indian Kanoon document link resolved from a matching search result title: {best_title}.",
    )


def _ensure_required_case_fields(analysis: dict) -> dict:
    defaults = {
        "applicant": "Not clearly named in the extracted materials.",
        "defendant": "Not clearly named in the extracted materials.",
        "charges": ["Not clearly identified from the extracted materials."],
        "demands": ["No demand extracted."],
        "arguments": [],
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
        case_name = citation.get("case_name", "").strip()
        if not case_name:
            continue

        link = str(citation.get("link", "") or "").strip()
        link_verified = bool(citation.get("link_verified", False))

        resolved_link, resolved_verified, resolved_note = _fetch_resolved_indiankanoon_doc_link(case_name)

        if link_verified and "indiankanoon.org/doc/" in link:
            citation["link"] = link
            citation["link_note"] = citation.get("link_note", "Direct link supplied and marked verified.")
            citation["link_verified"] = True
        else:
            citation["link"] = resolved_link
            citation["link_note"] = resolved_note
            citation["link_verified"] = resolved_verified

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
1. Identify the applicant.
2. Identify the defendant/respondent.
3. Identify the charges/offences involved.
4. Identify the applicant's demands.
5. Suggest better legal arguments to strengthen the applicant's case.
6. Suggest if "Non-application of mind" can be argued.
7. Find relevant Supreme Court or High Court citations.

Return JSON format:

{
 "applicant": "",
 "defendant": "",
 "charges": [],
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
Do not leave applicant, defendant, or charges blank. If the document is unclear, provide the best supported extraction or inference from the text.
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
