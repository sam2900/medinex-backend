from __future__ import annotations

from typing import List

from .schemas import PageText, TextChunk


def _split_words(text: str) -> List[str]:
    return text.split()


def build_chunks(
    pdf_name: str,
    pages: List[PageText],
    target_words: int = 180,
    overlap_words: int = 40,
) -> List[TextChunk]:
    chunks: List[TextChunk] = []

    for page in pages:
        words = _split_words(page.text or "")
        if not words:
            continue

        start = 0
        chunk_idx = 1

        while start < len(words):
            end = min(start + target_words, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words).strip()

            if chunk_text:
                chunks.append(
                    TextChunk(
                        chunk_id=f"p{page.page_num:03d}_c{chunk_idx:03d}",
                        pdf_name=pdf_name,
                        page_num=page.page_num,
                        text=chunk_text,
                    )
                )

            if end >= len(words):
                break

            start = max(0, end - overlap_words)
            chunk_idx += 1

    return chunks