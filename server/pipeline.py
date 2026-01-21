from __future__ import annotations

import csv
import datetime as dt
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader, PdfWriter

from .config import OCR_ENABLED, OUTPUT_DIR, PAST_TESTS_DB, PROBLEM_SETS_DIR, TESSERACT_CMD
from .utils import count_keyword_hits, normalize_subjects, parse_page_ranges


MATH_KEYWORDS = ["方程式", "関数", "図形", "確率", "資料", "比例", "一次関数", "二次関数"]
ENGLISH_KEYWORDS = ["文法", "語彙", "英作文", "長文", "読解", "リスニング", "対話文"]


def find_past_tests(school: str, grade: str, term: str) -> List[Path]:
    if not school or not grade:
        return []
    base = PAST_TESTS_DB / school / grade
    if not base.exists():
        return []
    pdfs = sorted(base.glob("*.pdf"))
    if term:
        pdfs = [path for path in pdfs if term in path.name]
    return pdfs


def find_problem_sets(publisher: str) -> Tuple[List[Path], List[Path], Path | None]:
    if not publisher:
        return [], [], None
    folder = PROBLEM_SETS_DIR / publisher
    if not folder.exists():
        return [], [], None
    questions_dir = folder / "questions"
    answers_dir = folder / "answers"
    questions = sorted(questions_dir.glob("*.pdf")) if questions_dir.exists() else []
    answers = sorted(answers_dir.glob("*.pdf")) if answers_dir.exists() else []
    page_map = folder / "page_map.csv"
    return questions, answers, page_map if page_map.exists() else None


def extract_text_pages(pdf_path: Path, enable_ocr: bool = False) -> List[str]:
    texts: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            texts.append(text.strip())

    if enable_ocr and _needs_ocr(texts):
        texts = _ocr_pdf(pdf_path, len(texts))

    return texts


def classify_page(text: str) -> str:
    if re.search(r"解答|答え|解説", text):
        return "answers"
    return "questions"


def build_ratio(texts: List[str], subjects: List[str]) -> List[Dict[str, str]]:
    combined_text = "\n".join(texts)
    results: List[Dict[str, str]] = []

    if "数学" in subjects:
        counts = {
            "数と式": count_keyword_hits(combined_text, ["方程式", "式", "計算"]),
            "関数": count_keyword_hits(combined_text, ["関数", "比例", "一次関数", "二次関数"]),
            "図形": count_keyword_hits(combined_text, ["図形", "角", "面積", "合同", "相似"]),
            "確率・資料": count_keyword_hits(combined_text, ["確率", "資料", "度数分布"]),
        }
        results.extend(_normalize_ratio(counts))

    if "英語" in subjects:
        counts = {
            "文法": count_keyword_hits(combined_text, ["文法", "語順", "時制", "助動詞"]),
            "読解": count_keyword_hits(combined_text, ["長文", "読解", "本文"]),
            "英作文": count_keyword_hits(combined_text, ["英作文", "作文"]),
            "リスニング": count_keyword_hits(combined_text, ["リスニング", "音声"]),
        }
        results.extend(_normalize_ratio(counts))

    if not results:
        results = [
            {"label": "数と式", "rate": 30},
            {"label": "関数", "rate": 25},
            {"label": "図形", "rate": 25},
            {"label": "確率・資料", "rate": 20},
        ]
    return results


def _normalize_ratio(counts: Dict[str, int]) -> List[Dict[str, str]]:
    total = sum(counts.values())
    if total <= 0:
        return [{"label": key, "rate": round(100 / len(counts))} for key in counts]
    normalized = []
    for key, value in counts.items():
        rate = round(value / total * 100)
        normalized.append({"label": key, "rate": rate})
    return normalized


def build_difficulty(texts: List[str]) -> List[Dict[str, str]]:
    combined = "\n".join(texts)
    short = len(re.findall(r"\b\d{1,2}\b", combined))
    long = len(re.findall(r"理由|説明|記述|英文で|証明", combined))
    total = max(short + long, 1)
    base = round(short / total * 100)
    standard = round((total - base) * 0.6)
    hard = 100 - base - standard
    return [
        {"level": "基礎", "detail": f"{base}%（短答中心）"},
        {"level": "標準", "detail": f"{standard}%（記述・応用）"},
        {"level": "応用", "detail": f"{hard}%（融合・長文）"},
    ]


def analyze_tests(school: str, grade: str, term: str, subjects: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], str]:
    past_tests = find_past_tests(school, grade, term)
    texts: List[str] = []
    for pdf in past_tests:
        texts.extend(extract_text_pages(pdf, enable_ocr=OCR_ENABLED))

    subject_list = normalize_subjects(subjects)
    ratio = build_ratio(texts, subject_list)
    difficulty = build_difficulty(texts)
    ocr_status = "完了" if texts else "未実施"
    return ratio, difficulty, ocr_status


def generate_mock_test(
    school: str,
    grade: str,
    term: str,
    publisher: str,
    range_text: str,
) -> Dict[str, str]:
    questions_sets, answers_sets, page_map_path = find_problem_sets(publisher)
    target_pages = parse_page_ranges(range_text)
    page_map = load_page_map(page_map_path) if page_map_path else {}
    auto_map = build_auto_page_map(questions_sets + answers_sets, target_pages) if not page_map else {}

    questions_writer = PdfWriter()
    answers_writer = PdfWriter()

    _append_pages_by_range(questions_sets, questions_writer, target_pages, page_map, auto_map, OCR_ENABLED)
    _append_pages_by_range(answers_sets, answers_writer, target_pages, page_map, auto_map, OCR_ENABLED)

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{school}_{grade}_{term}_{publisher}_{timestamp}".replace(" ", "")
    questions_path = OUTPUT_DIR / f"{base_name}_questions.pdf"
    answers_path = OUTPUT_DIR / f"{base_name}_answers.pdf"

    with questions_path.open("wb") as f:
        questions_writer.write(f)
    with answers_path.open("wb") as f:
        answers_writer.write(f)

    return {
        "questions_path": str(questions_path),
        "answers_path": str(answers_path),
    }


def load_page_map(path: Path | None) -> Dict[Tuple[str, int], List[int]]:
    if not path or not path.exists():
        return {}
    mapping: Dict[Tuple[str, int], List[int]] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                textbook_page = int(row["textbook_page"])
                pdf_page = int(row["pdf_page"])
                pdf_file = row["pdf_file"].strip()
            except (KeyError, ValueError, AttributeError):
                continue
            key = (pdf_file, textbook_page)
            mapping.setdefault(key, []).append(pdf_page - 1)
    return mapping


def _append_pages_by_range(
    pdfs: List[Path],
    writer: PdfWriter,
    target_pages: List[int],
    page_map: Dict[Tuple[str, int], List[int]],
    auto_map: Dict[Tuple[str, int], List[int]],
    enable_ocr: bool,
) -> None:
    for pdf_path in pdfs:
        reader = PdfReader(str(pdf_path))
        page_texts = extract_text_pages(pdf_path, enable_ocr=enable_ocr)
        for idx, page in enumerate(reader.pages):
            text = page_texts[idx] if idx < len(page_texts) else ""
            if target_pages:
                mapped_pages = set()
                for target in target_pages:
                    mapped_pages.update(page_map.get((pdf_path.name, target), []))
                    mapped_pages.update(auto_map.get((pdf_path.name, target), []))
                if mapped_pages:
                    if idx not in mapped_pages:
                        continue
                elif not _page_matches_range(text, target_pages):
                    continue
            writer.add_page(page)


def _page_matches_range(text: str, target_pages: List[int]) -> bool:
    if not text:
        return False
    for page_num in target_pages:
        if re.search(rf"(p\.?\s*{page_num}\b|ページ\s*{page_num}\b|\b{page_num}\b)", text):
            return True
    return False


def _needs_ocr(texts: List[str]) -> bool:
    if not texts:
        return False
    non_empty = sum(1 for t in texts if t.strip())
    return non_empty / len(texts) < 0.4


def _ocr_pdf(pdf_path: Path, page_count: int) -> List[str]:
    if TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    images = convert_from_path(str(pdf_path), dpi=300)
    texts: List[str] = []
    for image in images[:page_count]:
        text = pytesseract.image_to_string(image, lang="jpn+eng") or ""
        texts.append(text.strip())
    return texts


def build_auto_page_map(pdfs: List[Path], target_pages: List[int]) -> Dict[Tuple[str, int], List[int]]:
    if not target_pages:
        return {}
    mapping: Dict[Tuple[str, int], List[int]] = {}
    for pdf_path in pdfs:
        texts = extract_text_pages(pdf_path, enable_ocr=OCR_ENABLED)
        for idx, text in enumerate(texts):
            page_numbers = extract_textbook_pages(text)
            for page_num in page_numbers:
                if page_num in target_pages:
                    mapping.setdefault((pdf_path.name, page_num), []).append(idx)
    return mapping


def extract_textbook_pages(text: str) -> List[int]:
    if not text:
        return []
    matches = re.findall(r"(?:p\.?\s*|ページ\s*)(\d{1,3})", text, flags=re.IGNORECASE)
    return [int(m) for m in matches if m.isdigit()]
