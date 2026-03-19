from __future__ import annotations

from typing import Dict, List

from .llm_client import AzureOpenAIJsonClient
from .llm_table2 import extract_table2_with_llm
from .retrieval import LocalTfidfRetriever
from .schemas import ExtractedField, FieldEvidence, Table2StudyDetails


TABLE2_QUERIES = {
    "protocol_title": "official protocol title study title protocol title",
    "protocol_number": "protocol number study number protocol identifier",
    "phase": "study phase phase of study",
    "document_date": "document date protocol date approval date",
    "indication": "indication therapeutic area medical condition disease area",
}


def debug_table2_retrieval(
    pdf_name: str,
    retriever: LocalTfidfRetriever,
    top_k: int = 8,
) -> Dict:
    payload = {"pdf_name": pdf_name, "fields": []}

    for field_name, query in TABLE2_QUERIES.items():
        matches = retriever.search(query, top_k=top_k)
        field = FieldEvidence(
            field_name=field_name,
            query=query,
            matches=matches,
        )
        payload["fields"].append(field.model_dump())

    return payload


def _to_extracted_field(value: str | None) -> ExtractedField:
    if value is None or not str(value).strip():
        return ExtractedField(value=None, warning="No value extracted")
    return ExtractedField(
        value=str(value).strip(),
        method="llm_extraction",
        confidence=0.85,
    )


def extract_table2_study_details(
    pdf_name: str,
    retriever: LocalTfidfRetriever,
    top_k: int = 8,
    use_llm_fallback: bool = True,
) -> Table2StudyDetails:
    all_matches: List = []

    for query in TABLE2_QUERIES.values():
        all_matches.extend(retriever.search(query, top_k=top_k))

    if use_llm_fallback:
        client = AzureOpenAIJsonClient()
        data = extract_table2_with_llm(all_matches, client=client)
    else:
        data = {
            "protocol_date": None,
            "protocol_number": None,
            "indication": None,
            "phase": None,
            "protocol_title": None,
        }

    return Table2StudyDetails(
        pdf_name=pdf_name,
        protocol_title=_to_extracted_field(data.get("protocol_title")),
        protocol_number=_to_extracted_field(data.get("protocol_number")),
        phase=_to_extracted_field(data.get("phase")),
        document_date=_to_extracted_field(data.get("protocol_date")),
        indication=data.get("indication"),
    )