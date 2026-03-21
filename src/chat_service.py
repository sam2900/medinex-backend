from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.chunking import build_chunks
from src.llm_client import get_azure_llm_client
from src.pdf_ingest import extract_pdf_pages
from src.retrieval import LocalTfidfRetriever


def _pick_relevant_tables(question: str, extracted_result: dict[str, Any]) -> dict[str, Any]:
    """
    Simple first-pass table selection.
    Later you can make this smarter.
    """
    q = question.lower()

    table_map = {
        "table1": ["country", "fmv", "site budget"],
        "table2": ["study details", "protocol", "phase", "indication", "title", "date"],
        "table3": ["visit", "screening", "follow-up", "peri-anesthetic", "post-anesthetic"],
        "table4": ["procedure", "list of procedures", "table 4"],
        "table5": ["non procedure", "non-procedure", "crc", "pi", "staff labor"],
        "table6": ["site fee", "startup fee", "irb", "ethics", "close-out"],
        "table7": ["conditional", "imaging", "pk", "biomarker", "table 7"],
        "table8": ["patient cost", "travel", "meal", "hotel", "parking", "stipend"],
    }

    selected = {}
    for table_name, keywords in table_map.items():
        if any(k in q for k in keywords):
            if table_name in extracted_result:
                selected[table_name] = extracted_result[table_name]

    # Fallback: if nothing matched, include the lighter tables by default
    if not selected:
        for table_name in ["table1", "table2", "table3"]:
            if table_name in extracted_result:
                selected[table_name] = extracted_result[table_name]

    return selected


def _serialize_chunks(matches: list, max_chars: int = 1600) -> list[dict[str, Any]]:
    payload = []
    for m in matches:
        payload.append(
            {
                "chunk_id": getattr(m, "chunk_id", None),
                "page_num": getattr(m, "page_num", None),
                "score": getattr(m, "score", None),
                "text": (getattr(m, "text", "") or "")[:max_chars],
            }
        )
    return payload


def answer_question_about_protocol(
    pdf_path: str | Path,
    extracted_result: dict[str, Any],
    question: str,
    top_k: int = 6,
) -> dict[str, Any]:
    pdf_path = Path(pdf_path)

    pages = extract_pdf_pages(pdf_path)
    chunks = build_chunks(
        pdf_name=pdf_path.name,
        pages=pages,
        target_words=180,
        overlap_words=40,
    )
    retriever = LocalTfidfRetriever(chunks)
    matches = retriever.search(question, top_k=top_k)

    selected_tables = _pick_relevant_tables(question, extracted_result)

    system_prompt = """
You answer questions about a clinical trial protocol and its extracted budget tables.

Rules:
1. Use only the provided PDF chunks and extracted tables.
2. If the answer is not supported by the supplied context, say so clearly.
3. Prefer extracted tables for structured facts.
4. Use PDF chunks for evidence/explanation.
5. Keep answers concise and practical.
6. Return ONLY valid JSON.

Return JSON exactly like:
{
  "answer": "string",
  "confidence": "high|medium|low",
  "warnings": ["string"],
  "used_tables": ["table2", "table3"],
  "used_pages": [2, 21]
}
""".strip()

    user_prompt = f"""
Question:
{question}

Relevant extracted tables:
{json.dumps(selected_tables, indent=2, ensure_ascii=False)}

Relevant PDF chunks:
{json.dumps(_serialize_chunks(matches), indent=2, ensure_ascii=False)}
""".strip()

    client = get_azure_llm_client()
    result = client.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
    )

    return {
        "answer": result.get("answer", ""),
        "confidence": result.get("confidence", "low"),
        "warnings": result.get("warnings", []),
        "sources": {
            "tables": result.get("used_tables", []),
            "pages": result.get("used_pages", []),
            "retrieved_chunks": _serialize_chunks(matches, max_chars=400),
        },
    }