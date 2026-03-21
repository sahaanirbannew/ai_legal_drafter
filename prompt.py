# Prompt construction utilities for legal argument generation

def build_argument(case_json):

    text = "LEGAL ARGUMENT\n\n"

    text += "Applicant's Demands:\n"

    for d in case_json["demands"]:
        text += f"- {d}\n"

    text += "\nArguments:\n"

    for a in case_json["arguments"]:
        text += f"- {a}\n"

    text += "\nCitations:\n"

    for i,c in enumerate(case_json["citations"]):

        text += f"[{i+1}] {c['case_name']} ({c['court']})\n"

    return text