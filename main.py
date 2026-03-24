from fastapi import FastAPI, UploadFile
from pydantic import BaseModel
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import uuid
import os
import logging

from agentic_app.orchestrator import CaseWorkflowOrchestrator

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('ai_legal_drafter')

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

orchestrator = CaseWorkflowOrchestrator()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

validation_tasks = {}  # {task_id: {"status": "pending|complete|error", "result": ..., "error": ...}}


class CaseRequest(BaseModel):
    case_id: str


class FinalizeRequest(BaseModel):
    case_id: str
    edited_text: str
    comments: list[dict] = []

@app.post("/oovalidate")
async def oovalidate():
    logger.info('oovalidate started')
    try:
        raise ValueError('Direct validation without case_id is no longer supported')
        logger.info('oovalidate completed successfully')
        return {"validation": ""}
    except Exception as e:
        logger.error('oovalidate failed: %s', e, exc_info=True)
        return {"status": "error", "message": str(e)}


async def _run_validation_task(task_id):
    """Background task to run validation"""
    logger.info('Validation background task started for task_id=%s', task_id)
    try:
        task_info = validation_tasks[task_id]
        case_id = task_info["case_id"]
        case_state = orchestrator.validate(case_id)
        if case_state.status == "error":
            raise ValueError(case_state.errors[-1] if case_state.errors else "Validation failed")

        validation_tasks[task_id] = {
            "status": "complete",
            "result": case_state.validation_data or case_state.validation_text
        }
        logger.info('Validation task completed for task_id=%s', task_id)

    except Exception as e:
        logger.error('Validation task failed for task_id=%s: %s', task_id, e, exc_info=True)
        validation_tasks[task_id] = {
            "status": "error",
            "error": str(e),
            "result": {
                "validation_failed": True,
                "failure_reason": str(e),
                "overall_validity_score": None,
                "logic_score": None,
                "citation_validity_score": None,
                "issues_found": [str(e)],
                "suggested_improvements": [
                    "Retry validation after checking Gemini API availability, model configuration, and the uploaded PDF."
                ],
                "hallucinated_citations": [],
            }
        }


@app.post("/validate/start")
async def validate_start(request: CaseRequest):
    """Start validation task in background"""
    logger.info('Validation start endpoint called')
    try:
        task_id = str(uuid.uuid4())
        logger.info('Created task_id=%s for validation', task_id)

        validation_tasks[task_id] = {"status": "pending", "case_id": request.case_id}

        # Start background task
        asyncio.create_task(_run_validation_task(task_id))

        logger.info('Background validation task created for task_id=%s', task_id)
        return {"task_id": task_id, "status": "pending"}

    except Exception as e:
        logger.error('validate_start failed: %s', e, exc_info=True)
        return {"status": "error", "message": str(e)}


@app.get("/validate/status/{task_id}")
async def validate_status(task_id: str):
    """Check validation task status"""
    logger.debug('Validation status check for task_id=%s', task_id)
    try:
        if task_id not in validation_tasks:
            logger.warning('task_id=%s not found', task_id)
            return {"status": "error", "message": "Task not found"}

        task_info = validation_tasks[task_id]
        logger.debug('task_id=%s status=%s', task_id, task_info.get("status"))

        return task_info

    except Exception as e:
        logger.error('validate_status failed: %s', e, exc_info=True)
        return {"status": "error", "message": str(e)}



@app.post("/upload")
async def upload(file: UploadFile):
    logger.info('Upload started')
    try:
        case_state = orchestrator.ingest_upload(file.filename, file.file)
        if case_state.status == "error":
            raise ValueError(case_state.errors[-1] if case_state.errors else "Upload failed")
        logger.info('Upload completed successfully; case_id=%s', case_state.case_id)
        return {"status": "uploaded", "case_id": case_state.case_id}

    except Exception as e:
        logger.error('Upload failed: %s', e, exc_info=True)
        return {"status": "error", "message": str(e)}


@app.post("/analyze")
async def analyze(request: CaseRequest):
    logger.info('Analysis started')
    try:
        case_state = orchestrator.analyze(request.case_id)
        if case_state.status == "error":
            raise ValueError(case_state.errors[-1] if case_state.errors else "Analysis failed")
        case_state = orchestrator.draft(request.case_id)
        if case_state.status == "error":
            raise ValueError(case_state.errors[-1] if case_state.errors else "Drafting failed")

        logger.info('Analysis completed successfully')
        return {
            "text": case_state.draft_text,
            "citations": case_state.analysis["citations"],
            "case_id": case_state.case_id,
        }

    except Exception as e:
        logger.error('Analysis failed: %s', e, exc_info=True)
        return {"status": "error", "message": str(e)}


@app.post("/oogenerate_pdf")
async def oogenerate_pdf():
    logger.info('oogenerate_pdf started')
    try:
        raise ValueError('Direct PDF generation without case_id is no longer supported')

    except Exception as e:
        logger.error('oogenerate_pdf failed: %s', e, exc_info=True)
        return {"status": "error", "message": str(e)}


@app.post("/generate_pdf")
async def generate_pdf(request: CaseRequest):
    logger.info('generate_pdf started')
    try:
        case_state = orchestrator.generate_outputs(request.case_id)
        if case_state.status == "error":
            raise ValueError(case_state.errors[-1] if case_state.errors else "PDF generation failed")

        path = case_state.artifacts["download_pdf"]
        filename = os.path.basename(path)
        logger.info('generate_pdf completed successfully: %s', path)
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=filename
        )

    except Exception as e:
        logger.error('generate_pdf failed: %s', e, exc_info=True)
        return {"status": "error", "message": str(e)}


@app.post("/finalize_pdf")
async def finalize_pdf(request: FinalizeRequest):
    logger.info('finalize_pdf started')
    try:
        case_state = orchestrator.finalize_and_generate(
            request.case_id,
            request.edited_text,
            request.comments,
        )
        if case_state.status == "error":
            raise ValueError(case_state.errors[-1] if case_state.errors else "Finalization failed")

        path = case_state.artifacts["download_pdf"]
        filename = os.path.basename(path)
        logger.info('finalize_pdf completed successfully: %s', path)
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=filename
        )
    except Exception as e:
        logger.error('finalize_pdf failed: %s', e, exc_info=True)
        return {"status": "error", "message": str(e)}


@app.get("/cases/{case_id}")
async def get_case(case_id: str):
    logger.debug('Fetching case state for case_id=%s', case_id)
    try:
        case_state = orchestrator.get_case(case_id)
        return case_state.to_dict()
    except Exception as e:
        logger.error('get_case failed: %s', e, exc_info=True)
        return {"status": "error", "message": str(e)}
