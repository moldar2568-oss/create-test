from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import OUTPUT_DIR
from .pipeline import analyze_tests, generate_mock_test


BASE_DIR = Path(__file__).resolve().parent.parent


class AnalyzeRequest(BaseModel):
    school: str = ""
    grade: str = ""
    term: str = ""
    publisher: str = ""
    range: str = ""
    subjects: str = ""


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


app.mount("/generated", StaticFiles(directory=OUTPUT_DIR), name="generated")


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> dict:
    ratio, difficulty, ocr_status = analyze_tests(
        payload.school,
        payload.grade,
        payload.term,
        payload.subjects,
    )
    return {"ratio": ratio, "difficulty": difficulty, "ocr_status": ocr_status}


@app.post("/api/generate")
def generate(payload: AnalyzeRequest) -> dict:
    paths = generate_mock_test(
        payload.school,
        payload.grade,
        payload.term,
        payload.publisher,
        payload.range,
    )
    questions_url = f"/generated/{Path(paths['questions_path']).name}"
    answers_url = f"/generated/{Path(paths['answers_path']).name}"
    return {"questions_url": questions_url, "answers_url": answers_url}
