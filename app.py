from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hmac
import os
import shutil
from pathlib import Path
from uuid import uuid4

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.chat_service import answer_question_about_protocol
from src.llm_client import get_azure_llm_client
from src.pipeline_service import run_protocol_pipeline
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="Protocol Budget Extraction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # "http://localhost:8080",
        # "http://127.0.0.1:8080",
        "https://medinex-hub.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Simple in-memory job store for V1
# Later move this to Redis / DB / Blob metadata if needed.
JOB_STORE: dict[str, dict] = {}
APP_AUTH_USERNAME = os.getenv("APP_AUTH_USERNAME", "")
APP_AUTH_PASSWORD = os.getenv("APP_AUTH_PASSWORD", "")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
bearer_scheme = HTTPBearer(auto_error=False)


class ChatRequest(BaseModel):
    job_id: str
    question: str


class LoginRequest(BaseModel):
    username: str
    password: str


def _require_auth_configuration() -> None:
    missing = [
        name
        for name, value in {
            "APP_AUTH_USERNAME": APP_AUTH_USERNAME,
            "APP_AUTH_PASSWORD": APP_AUTH_PASSWORD,
            "JWT_SECRET_KEY": JWT_SECRET_KEY,
        }.items()
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing auth configuration: {', '.join(missing)}",
        )


def _create_access_token(username: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    _require_auth_configuration()

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token.") from exc

    username = str(payload.get("sub", "")).strip()
    if not username or not hmac.compare_digest(username, APP_AUTH_USERNAME):
        raise HTTPException(status_code=401, detail="Invalid token subject.")

    return username


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


@app.post("/auth/login")
def login(payload: LoginRequest) -> dict:
    _require_auth_configuration()

    username_ok = hmac.compare_digest(payload.username, APP_AUTH_USERNAME)
    password_ok = hmac.compare_digest(payload.password, APP_AUTH_PASSWORD)

    if not username_ok or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = _create_access_token(APP_AUTH_USERNAME)
    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "expires_in_minutes": JWT_EXPIRE_MINUTES,
    }


@app.get("/health/llm")
def health_llm(_: str = Depends(require_authenticated_user)):
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
async def extract_protocol(
    file: UploadFile = File(...),
    _: str = Depends(require_authenticated_user),
) -> dict:
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
async def extract_and_download(
    file: UploadFile = File(...),
    _: str = Depends(require_authenticated_user),
) -> FileResponse:
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
def download_excel(
    job_id: str,
    _: str = Depends(require_authenticated_user),
) -> FileResponse:
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
def chat_about_protocol(
    payload: ChatRequest,
    _: str = Depends(require_authenticated_user),
) -> dict:
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
