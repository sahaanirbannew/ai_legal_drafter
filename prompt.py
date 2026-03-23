# Prompt construction utilities for legal argument generation

def build_argument(case_json):

    text = "LEGAL ARGUMENT\n\n"

    text += f"Applicant: {case_json.get('applicant', 'Not clearly identified')}\n"
    text += f"Defendant/Respondent: {case_json.get('defendant', 'Not clearly identified')}\n"

    text += "\nCharges/Offences:\n"

    for charge in case_json.get("charges", []):
        text += f"- {charge}\n"

    text += "\n"
    text += "Applicant's Demands:\n"

    for d in case_json.get("demands", []):
        text += f"- {d}\n"

    text += "\nArguments:\n"

    for a in case_json.get("arguments", []):
        text += f"- {a}\n"

    text += "\nCitations:\n"

    for i,c in enumerate(case_json.get("citations", [])):

        text += f"[{i+1}] {c['case_name']} ({c['court']})\n"

    return text
