from __future__ import annotations

from typing import Dict

from .llm_client import AzureOpenAIJsonClient
from .llm_table1 import extract_table1_with_llm
from .retrieval import LocalTfidfRetriever
from .schemas import FieldEvidence, Table1BudgetEstimationDetails, Table1BudgetRow


TABLE1_QUERY = (
    "country countries region site country summary country 1 country-specific "
    "study locations protocol country clinicaltrials.gov country"
)


def debug_table1_retrieval(
    pdf_name: str,
    retriever: LocalTfidfRetriever,
    top_k: int = 10,
) -> Dict:
    matches = retriever.search(TABLE1_QUERY, top_k=top_k)
    field = FieldEvidence(
        field_name="table1_budget_estimation",
        query=TABLE1_QUERY,
        matches=matches,
    )
    return {
        "pdf_name": pdf_name,
        "fields": [field.model_dump()],
    }


def extract_table1_budget_estimation(
    pdf_name: str,
    retriever: LocalTfidfRetriever,
    top_k: int = 10,
    use_llm_fallback: bool = True,
) -> Table1BudgetEstimationDetails:
    matches = retriever.search(TABLE1_QUERY, top_k=top_k)

    country = ""

    if use_llm_fallback:
        client = AzureOpenAIJsonClient()
        data = extract_table1_with_llm(matches, client=client)
        country = str(data.get("country", "")).strip()

    rows = [
        Table1BudgetRow(category="Country", details=country),
        Table1BudgetRow(category="FMV", details="Low"),
    ]

    return Table1BudgetEstimationDetails(
        pdf_name=pdf_name,
        items=rows,
    )