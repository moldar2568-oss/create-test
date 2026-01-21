from __future__ import annotations

import re
from typing import Iterable, List, Set


def parse_page_ranges(text: str) -> List[int]:
    if not text:
        return []

    pages: Set[int] = set()
    normalized = text.replace("〜", "-").replace("~", "-")
    for match in re.finditer(r"(\d{1,3})\s*-\s*(\d{1,3})", normalized):
        start = int(match.group(1))
        end = int(match.group(2))
        if start > end:
            start, end = end, start
        pages.update(range(start, end + 1))

    for match in re.finditer(r"(?<!\d)(\d{1,3})(?!\d)", normalized):
        pages.add(int(match.group(1)))

    return sorted(pages)


def normalize_subjects(subjects: str) -> List[str]:
    if not subjects:
        return []
    return [s for s in re.split(r"[・/,\s]+", subjects) if s]


def count_keyword_hits(text: str, keywords: Iterable[str]) -> int:
    if not text:
        return 0
    return sum(len(re.findall(keyword, text)) for keyword in keywords)
