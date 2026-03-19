from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.pipeline_service import run_protocol_pipeline
from src.llm_client import get_azure_llm_client

app = FastAPI(title="Protocol Budget Extraction API")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/extract")
async def extract_protocol(file: UploadFile = File(...)) -> dict:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    safe_name = f"{uuid4().hex}_{file.filename}"
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
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-and-download")
async def extract_and_download(file: UploadFile = File(...)) -> FileResponse:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    safe_name = f"{uuid4().hex}_{file.filename}"
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
        excel_path = Path(result["excel_path"])
        return FileResponse(
            path=excel_path,
            filename=excel_path.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
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