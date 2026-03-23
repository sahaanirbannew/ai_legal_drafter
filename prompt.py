# Prompt construction utilities for legal argument generation

def build_argument(case_json):
    plan = case_json.get("plan_of_action", {}) or {}
    plan_reasons = plan.get("reasons", []) or []

    text = "LEGAL ARGUMENT\n\n"

    text += f"Applicant: {case_json.get('applicant', 'Not clearly identified')}\n"
    text += f"Defendant/Respondent: {case_json.get('defendant', 'Not clearly identified')}\n"
    text += f"Court/Forum: {case_json.get('forum', 'Not clearly identified')}\n"
    text += f"Authority to approach the Court: {case_json.get('authority_to_approach_court', 'Not clearly identified')}\n"

    text += "\nCharges/Offences:\n"

    for charge in case_json.get("charges", []):
        text += f"- {charge}\n"

    text += "\n"
    text += "Jurisdiction and Maintainability:\n"
    text += f"- The present matter is placed before {case_json.get('forum', 'the appropriate court')} under {case_json.get('authority_to_approach_court', 'the legal authority stated in the case papers')}.\n"

    text += "\n"
    text += "Applicant's Demands:\n"

    for d in case_json.get("demands", []):
        text += f"- {d}\n"

    text += "\nArguments:\n"

    for a in case_json.get("arguments", []):
        text += f"- {a}\n"

    text += "\nPlan of Action:\n"
    text += f"- Filing recommendation: {plan.get('filing_recommendation', 'Not clearly identified')}\n"
    text += f"- Appropriate remedy to seek: {plan.get('recommended_remedy', 'Not clearly identified')}\n"
    for reason in plan_reasons:
        text += f"- Reason: {reason}\n"

    text += "\nCitations:\n"

    for i,c in enumerate(case_json.get("citations", [])):

        text += f"[{i+1}] {c['case_name']} ({c['court']})\n"

    return text
