from __future__ import annotations

from typing import Dict

from .llm_client import AzureOpenAIJsonClient
from .llm_source_selector import select_protocol_source_with_llm
from .retrieval import LocalTfidfRetriever
from .schemas import FieldEvidence, ProtocolSourceSelection, SourceTableChoice


SOURCE_SELECTOR_QUERY = (
    "schedule of activities summary table summary tables evaluations during "
    "follow-up evaluations end of treatment treatment schedule assessment schedule "
    "appendix schedule of activities visit schedule"
)


def debug_source_selector_retrieval(
    pdf_name: str,
    retriever: LocalTfidfRetriever,
    top_k: int = 18,
) -> Dict:
    matches = retriever.search(SOURCE_SELECTOR_QUERY, top_k=top_k)
    field = FieldEvidence(
        field_name="source_selector",
        query=SOURCE_SELECTOR_QUERY,
        matches=matches,
    )
    return {
        "pdf_name": pdf_name,
        "fields": [field.model_dump()],
    }


def select_protocol_source(
    pdf_name: str,
    retriever: LocalTfidfRetriever,
    top_k: int = 18,
) -> ProtocolSourceSelection:
    matches = retriever.search(SOURCE_SELECTOR_QUERY, top_k=top_k)

    client = AzureOpenAIJsonClient()
    data = select_protocol_source_with_llm(matches=matches, client=client)

    primary = [
        SourceTableChoice(
            label=str(x.get("label", "")).strip(),
            page_hint=x.get("page_hint"),
            reason=str(x.get("reason", "")).strip(),
        )
        for x in (data.get("primary_tables", []) or [])
    ]

    secondary = [
        SourceTableChoice(
            label=str(x.get("label", "")).strip(),
            page_hint=x.get("page_hint"),
            reason=str(x.get("reason", "")).strip(),
        )
        for x in (data.get("secondary_tables", []) or [])
    ]

    notes = [str(x).strip() for x in (data.get("notes", []) or []) if str(x).strip()]

    return ProtocolSourceSelection(
        pdf_name=pdf_name,
        source_type=str(data.get("source_type", "")).strip(),
        confidence=str(data.get("confidence", "")).strip(),
        primary_tables=primary,
        secondary_tables=secondary,
        notes=notes,
    )


def debug_source_selector_trace(
    pdf_name: str,
    retriever: LocalTfidfRetriever,
    top_k: int = 18,
) -> Dict:
    matches = retriever.search(SOURCE_SELECTOR_QUERY, top_k=top_k)

    client = AzureOpenAIJsonClient()
    llm_data = select_protocol_source_with_llm(matches=matches, client=client)

    return {
        "pdf_name": pdf_name,
        "retrieval_debug": FieldEvidence(
            field_name="source_selector",
            query=SOURCE_SELECTOR_QUERY,
            matches=matches,
        ).model_dump(),
        "llm_raw_output": llm_data,
    }