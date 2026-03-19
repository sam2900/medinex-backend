from __future__ import annotations

from pathlib import Path
from typing import List

import fitz  # PyMuPDF

from .schemas import PageText


def extract_pdf_pages(pdf_path: Path) -> List[PageText]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages: List[PageText] = []
    with fitz.open(pdf_path) as doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            normalized = " ".join(text.split())
            pages.append(PageText(page_num=index, text=normalized))
    return pages
