from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import shutil
import os
from datetime import datetime
from dotenv import load_dotenv
from gemini_validator import validate_case
from openai import OpenAI
from openai_client import analyze_case
from prompt import build_argument
from pdf_generator import create_pdf

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load .env and read OPENAI_API_KEY
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file or environment variables.")

client = OpenAI(api_key=openai_api_key)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

file_id_store = None
case_json_store = None
generated_text = None

@app.post("/oovalidate")
async def validate():

    result = validate_case(
        "uploads/original_case.pdf",
        "output_case.pdf",
        case_json_store
    )

    return {"validation": result}

@app.post("/validate")
async def validate():

    validation = validate_case(
        "uploads/original_case.pdf",
        "output_case.pdf",
        case_json_store
    )

    validation_text = f"\n\nVALIDATION REPORT\n\n{validation}"

    final_text = generated_text + validation_text

    create_pdf(final_text, "validated_case.pdf")

    return {"validation": validation}

@app.post("/upload")
async def upload(file: UploadFile):

    path = f"uploads/{file.filename}"

    with open(path,"wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    uploaded = client.files.create(
        file=open(path,"rb"),
        purpose="assistants"
    )

    global file_id_store
    file_id_store = uploaded.id

    return {"status":"uploaded"}


@app.post("/analyze")
async def analyze():

    global case_json_store
    global generated_text

    case_json_store = analyze_case(file_id_store)

    generated_text = build_argument(case_json_store)

    return {
        "text": generated_text,
        "citations": case_json_store["citations"]
    }


@app.post("/oogenerate_pdf")
async def generate_pdf():

    path = "output_case.pdf"

    create_pdf(generated_text, path)

    return {"pdf":path}

@app.post("/generate_pdf")
async def generate_pdf():

    downloads_dir = os.path.expanduser("~/Downloads")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"legal_argument_{timestamp}.pdf"
    path = os.path.join(downloads_dir, filename)

    create_pdf(generated_text, path)

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename
    )