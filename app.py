from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.chat_service import answer_question_about_protocol
from src.llm_client import get_azure_llm_client
from src.pipeline_service import run_protocol_pipeline

app = FastAPI(title="Protocol Budget Extraction API")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Simple in-memory job store for V1
# Later move this to Redis / DB / Blob metadata if needed.
JOB_STORE: dict[str, dict] = {}


class ChatRequest(BaseModel):
    job_id: str
    question: str


def _format_extract_response(job_id: str, result: dict) -> dict:
    return {
        "status": "success",
        "job_id": job_id,
        "pdf_name": result["pdf_name"],
        "tables": {
            "table1": result["table1"],
            "table2": result["table2"],
            "table3": result["table3"],
            "table4": result["table4"],
            "table5": result["table5"],
            "table6": result["table6"],
            "table7": result["table7"],
            "table8": result["table8"],
        },
        "artifacts": {
            "excel_path": result["excel_path"],
            "excel_download_url": f"/download/{job_id}",
        },
        "warnings": [],
        "meta": {
            "used_llm": True,
            "version": "v1",
        },
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/health/llm")
def health_llm():
    try:
        client = get_azure_llm_client()
        result = client.complete_json(
            system_prompt="Return valid JSON.",
            user_prompt='Return {"status":"ok"}',
            temperature=0.0,
        )
        return {"status": "ok", "llm": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract")
async def extract_protocol(file: UploadFile = File(...)) -> dict:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    job_id = uuid4().hex
    safe_name = f"{job_id}_{file.filename}"
    pdf_path = UPLOAD_DIR / safe_name

    with pdf_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        result = run_protocol_pipeline(
            pdf_path=pdf_path,
            output_dir=OUTPUT_DIR,
            use_llm=True,
            top_k=18,
        )

        response = _format_extract_response(job_id=job_id, result=result)

        JOB_STORE[job_id] = {
            "job_id": job_id,
            "pdf_path": str(pdf_path),
            "result": response,
        }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-and-download")
async def extract_and_download(file: UploadFile = File(...)) -> FileResponse:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    job_id = uuid4().hex
    safe_name = f"{job_id}_{file.filename}"
    pdf_path = UPLOAD_DIR / safe_name

    with pdf_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        result = run_protocol_pipeline(
            pdf_path=pdf_path,
            output_dir=OUTPUT_DIR,
            use_llm=True,
            top_k=18,
        )

        response = _format_extract_response(job_id=job_id, result=result)

        JOB_STORE[job_id] = {
            "job_id": job_id,
            "pdf_path": str(pdf_path),
            "result": response,
        }

        excel_path = Path(result["excel_path"])
        return FileResponse(
            path=excel_path,
            filename=excel_path.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{job_id}")
def download_excel(job_id: str) -> FileResponse:
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    excel_path = Path(job["result"]["artifacts"]["excel_path"])
    if not excel_path.exists():
        raise HTTPException(status_code=404, detail="Excel file not found.")

    return FileResponse(
        path=excel_path,
        filename=excel_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.post("/chat")
def chat_about_protocol(payload: ChatRequest) -> dict:
    job = JOB_STORE.get(payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found. Upload/extract the PDF first.")

    try:
        chat_result = answer_question_about_protocol(
            pdf_path=job["pdf_path"],
            extracted_result=job["result"]["tables"],
            question=payload.question,
            top_k=6,
        )

        return {
            "status": "success",
            "job_id": payload.job_id,
            "question": payload.question,
            "answer": chat_result["answer"],
            "confidence": chat_result["confidence"],
            "warnings": chat_result["warnings"],
            "sources": chat_result["sources"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))