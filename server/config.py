from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PAST_TESTS_DB = Path(os.getenv("PAST_TESTS_DB", BASE_DIR / "past_tests_db"))
PROBLEM_SETS_DIR = Path(os.getenv("PROBLEM_SETS_DIR", BASE_DIR / "problem_sets"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "generated"))
OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
