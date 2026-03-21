# OpenAI API client helper functions

import os
from dotenv import load_dotenv
from openai import OpenAI
import json

# Load environment variables from .env file
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise EnvironmentError("OPENAI_API_KEY not set in environment or .env file")

client = OpenAI(api_key=openai_api_key)


def analyze_case(file_id):

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
   "link":""
  }
 ]
}

IMPORTANT:
Only cite real cases.
Prefer Supreme Court cases.
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

    return json.loads(response.output_text)