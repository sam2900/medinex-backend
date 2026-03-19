from __future__ import annotations

from typing import Dict, List

from .llm_client import AzureOpenAIJsonClient
from .llm_table3 import construct_table3_budget_visits, extract_table3_soa_evidence
from .retrieval import LocalTfidfRetriever
from .schemas import FieldEvidence, Table3VisitDetails, Table3VisitRow
from .source_selector import select_protocol_source


TABLE3_QUERY_SOA = (
    "schedule of activities appendix schedule of activities visit schedule "
    "screening baseline follow-up follow up treatment discontinuation off-treatment "
    "long term follow up unscheduled visit q2w q4w q8w footnotes notes "
    "peri-anesthetic post-anesthetic day 14 week 2 week 4 week 6 week 8 week 10 week 12 "
    "until progression disease assessment tumor assessment ct mri clinically indicated"
)

TABLE3_QUERY_SUMMARY = (
    "summary table summary tables evaluations during follow-up evaluations "
    "end of treatment treatment schedule assessment schedule visit schedule "
    "screening baseline follow-up follow up discontinuation treatment period follow-up"
)


def _get_table3_query(source_type: str) -> str:
    if source_type == "summary_table":
        return TABLE3_QUERY_SUMMARY
    if source_type == "hybrid":
        return TABLE3_QUERY_SUMMARY + " " + TABLE3_QUERY_SOA
    return TABLE3_QUERY_SOA


def debug_table3_retrieval(
    pdf_name: str,
    retriever: LocalTfidfRetriever,
    top_k: int = 16,
) -> Dict:
    source_selection = select_protocol_source(
        pdf_name=pdf_name,
        retriever=retriever,
        top_k=top_k,
    )

    query = _get_table3_query(source_selection.source_type)
    matches = retriever.search(query, top_k=top_k)

    field = FieldEvidence(
        field_name="table3_visit_schedule",
        query=query,
        matches=matches,
    )
    return {
        "pdf_name": pdf_name,
        "source_selection": source_selection.model_dump(),
        "fields": [field.model_dump()],
    }


def debug_table3_trace(
    pdf_name: str,
    retriever: LocalTfidfRetriever,
    top_k: int = 16,
) -> Dict:
    source_selection = select_protocol_source(
        pdf_name=pdf_name,
        retriever=retriever,
        top_k=top_k,
    )

    query = _get_table3_query(source_selection.source_type)
    matches = retriever.search(query, top_k=top_k)
    client = AzureOpenAIJsonClient()

    soa_evidence = extract_table3_soa_evidence(matches, client=client)
    budget_visits = construct_table3_budget_visits(soa_evidence, client=client)

    raw_rows = _rows_from_budget_visits_payload(budget_visits)
    normalized_rows = _normalize_table3_rows(
        pdf_name=pdf_name,
        rows=raw_rows,
        source_type=source_selection.source_type,
    )

    return {
        "pdf_name": pdf_name,
        "source_selection": source_selection.model_dump(),
        "retrieval_debug": FieldEvidence(
            field_name="table3_visit_schedule",
            query=query,
            matches=matches,
        ).model_dump(),
        "soa_evidence": soa_evidence,
        "budget_visit_construction": budget_visits,
        "normalized_visits": [r.model_dump() for r in normalized_rows],
    }


def _normalize_visit_title(value: str) -> str:
    v = " ".join((value or "").split()).strip()

    replacements = {
        "Off Treatment Visit": "Off-Tx Visit",
        "Off-Treatment Visit": "Off-Tx Visit",
        "Off Tx Visit": "Off-Tx Visit",
        "Off-Treatment Visits": "Off-Tx Visit",
        "Off Treatment Visits": "Off-Tx Visit",
        "Long-Term Follow-Up": "Long term follow up",
        "Long Term Follow-Up": "Long term follow up",
        "Long-Term Follow up": "Long term follow up",
        "Long Term Follow up": "Long term follow up",
        "Unscheduled visit": "Unscheduled Visit",
        "Follow up (Day 14)": "Follow-up (Day 14)",
        "Follow-Up (Day 14)": "Follow-up (Day 14)",
        "Treatment Discontinuation (Day 28 post final dose)": "Treatment Discontinuation",
        "Screening (Days -14 to -1)": "Screening (Days -28 to -1)",
        "Visit 1/Screening": "Screening (Days -28 to -1)",
        "Visit 2/Peri-anesthetic period": "Peri-anesthetic (Day 1)",
        "Visit 3/Post-anesthetic period": "Post-anesthetic (4-36h)",
        "Visit 4/Follow-up contact": "Follow-up (Day 14)",
    }

    return replacements.get(v, v)


def _normalize_visit_id(value: str, title: str = "") -> str:
    v = " ".join((value or "").split()).strip().upper()
    t = " ".join((title or "").split()).strip().lower()

    if t == "screening (days -28 to -1)":
        return "SCR"
    if t == "baseline (week 1)":
        return "BW1"
    if t == "treatment discontinuation":
        return "TD"
    if t == "off-tx visit":
        return "OFFTX"
    if t == "long term follow up":
        return "LTFU"
    if t == "unscheduled visit":
        return "USV"
    if t == "follow-up (day 14)":
        return "FU14"
    if t == "peri-anesthetic (day 1)":
        return "V2"
    if t == "post-anesthetic (4-36h)":
        return "V3"

    replacements = {
        "SCREENING": "SCR",
        "UNSCHEDULED": "USV",
        "UNSCHEDULED VISIT": "USV",
        "OFF-TREATMENT": "OFFTX",
        "OFF-TX": "OFFTX",
        "LONG TERM FOLLOW UP": "LTFU",
        "LONG-TERM FOLLOW-UP": "LTFU",
        "TREATMENT DISCONTINUATION": "TD",
        "VISIT 2": "V2",
        "VISIT 3": "V3",
        "VISIT 4": "FU14",
    }

    return replacements.get(v, v or "")


def _rows_from_budget_visits_payload(payload: dict) -> List[Table3VisitRow]:
    rows: List[Table3VisitRow] = []

    for item in payload.get("visits", []) or []:
        raw_title = str(item.get("visit_title", "")).strip()
        raw_id = str(item.get("visit_id", "")).strip()

        title = _normalize_visit_title(raw_title)
        visit_id = _normalize_visit_id(raw_id, title=title)

        if not title or not visit_id:
            continue

        rows.append(Table3VisitRow(visit_title=title, visit_id=visit_id))

    return rows


def _dedupe_preserve_order(rows: List[Table3VisitRow]) -> List[Table3VisitRow]:
    seen = set()
    out: List[Table3VisitRow] = []

    for row in rows:
        key = (row.visit_title.strip().lower(), row.visit_id.strip().upper())
        if key in seen:
            continue
        seen.add(key)
        out.append(row)

    return out


def _ensure_usv(rows: List[Table3VisitRow]) -> List[Table3VisitRow]:
    if any(r.visit_id.strip().upper() == "USV" for r in rows):
        return rows
    rows.append(Table3VisitRow(visit_title="Unscheduled Visit", visit_id="USV"))
    return rows


def _drop_invalid_cadence_rows(rows: List[Table3VisitRow]) -> List[Table3VisitRow]:
    """
    Generic cleanup:
    - remove disease/tumor/imaging-only pseudo visits
    - remove mechanically expanded Q4Wxx rows
    """
    filtered: List[Table3VisitRow] = []

    for row in rows:
        title_l = row.visit_title.strip().lower()
        vid = row.visit_id.strip().upper()

        if "tumor assessment" in title_l:
            continue
        if "disease assessment" in title_l:
            continue
        if "mri" in title_l or "ct scan" in title_l:
            continue

        # Do not keep explicit expanded Q4W week rows in normalized budgeting output
        if title_l.startswith("q4w (week "):
            continue
        if vid.startswith("Q4W") and vid != "Q4W":
            continue

        filtered.append(row)

    return filtered


def _normalize_summary_table_rows(rows: List[Table3VisitRow]) -> List[Table3VisitRow]:
    """
    Summary-table-based protocols like Protocol 003:
    normalize to SCR / V2 / V3 / FU14 / USV.
    """
    out: List[Table3VisitRow] = []

    for row in rows:
        t = row.visit_title.strip().lower()
        vid = row.visit_id.strip().upper()

        # screening
        if "screen" in t or vid == "SCR":
            out.append(Table3VisitRow(visit_title="Screening (Days -28 to -1)", visit_id="SCR"))
            continue

        # peri-anesthetic
        if "peri-anesthetic" in t or vid == "V2":
            out.append(Table3VisitRow(visit_title="Peri-anesthetic (Day 1)", visit_id="V2"))
            continue

        # post-anesthetic
        if "post-anesthetic" in t or vid == "V3":
            out.append(Table3VisitRow(visit_title="Post-anesthetic (4-36h)", visit_id="V3"))
            continue

        # follow-up
        if "follow-up" in t or "follow up" in t or vid in {"V4", "FU14"}:
            out.append(Table3VisitRow(visit_title="Follow-up (Day 14)", visit_id="FU14"))
            continue

        # unscheduled
        if vid == "USV" or "unscheduled" in t:
            out.append(Table3VisitRow(visit_title="Unscheduled Visit", visit_id="USV"))
            continue

    out = _dedupe_preserve_order(out)
    out = _ensure_usv(out)
    return out


def _normalize_soa_rows(rows: List[Table3VisitRow]) -> List[Table3VisitRow]:
    """
    SoA-based protocols:
    keep named visits and normalized cadence rows, but avoid blind cadence expansion.
    """
    rows = _drop_invalid_cadence_rows(rows)

    # If we have a simple explicit-visit study (like Protocol 003), normalize those
    explicit_titles = " ".join(r.visit_title.lower() for r in rows)
    if "peri-anesthetic" in explicit_titles or "post-anesthetic" in explicit_titles:
        return _normalize_summary_table_rows(rows)

    # Collapse Q4W to a single normalized recurring row if any Q4W existed
    has_q4w = any(
        r.visit_id == "Q4W" or r.visit_title.strip().lower().startswith("q4w")
        for r in rows
    )

    rows = [r for r in rows if not (r.visit_id == "Q4W" or r.visit_title.strip().lower().startswith("q4w"))]

    # Remove commonly invalid mechanically-generated Q2W rows if they appear
    rows = [
        r for r in rows
        if r.visit_id not in {"Q2W4", "Q2W8"}
        and r.visit_title not in {"Q2W (Week 4)", "Q2W (Week 8)"}
    ]

    # Insert normalized Q4W before TD if any Q4W cadence exists
    if has_q4w:
        q4w_row = Table3VisitRow(visit_title="Q4W (until PD)", visit_id="Q4W")
        inserted = False
        out: List[Table3VisitRow] = []
        for r in rows:
            if not inserted and r.visit_id == "TD":
                out.append(q4w_row)
                inserted = True
            out.append(r)
        if not inserted:
            out.append(q4w_row)
        rows = out

    rows = _dedupe_preserve_order(rows)
    rows = _ensure_usv(rows)
    return rows


def _normalize_table3_rows(
    pdf_name: str,
    rows: List[Table3VisitRow],
    source_type: str,
) -> List[Table3VisitRow]:
    if source_type == "summary_table":
        return _normalize_summary_table_rows(rows)

    if source_type == "hybrid":
        # hybrid: try SoA normalization first, then fallback to summary-like explicit visits
        rows = _normalize_soa_rows(rows)
        rows = _dedupe_preserve_order(rows)
        rows = _ensure_usv(rows)
        return rows

    rows = _normalize_soa_rows(rows)
    rows = _dedupe_preserve_order(rows)
    rows = _ensure_usv(rows)
    return rows


def extract_table3_visit_details(
    pdf_name: str,
    retriever: LocalTfidfRetriever,
    top_k: int = 16,
    use_llm_fallback: bool = True,
) -> Table3VisitDetails:
    source_selection = select_protocol_source(
        pdf_name=pdf_name,
        retriever=retriever,
        top_k=top_k,
    )
    query = _get_table3_query(source_selection.source_type)
    matches = retriever.search(query, top_k=top_k)

    if not use_llm_fallback:
        return Table3VisitDetails(
            pdf_name=pdf_name,
            visits=[Table3VisitRow(visit_title="Unscheduled Visit", visit_id="USV")],
        )

    client = AzureOpenAIJsonClient()
    soa_evidence = extract_table3_soa_evidence(matches, client=client)
    budget_visits = construct_table3_budget_visits(soa_evidence, client=client)

    raw_rows = _rows_from_budget_visits_payload(budget_visits)
    rows = _normalize_table3_rows(
        pdf_name=pdf_name,
        rows=raw_rows,
        source_type=source_selection.source_type,
    )

    return Table3VisitDetails(pdf_name=pdf_name, visits=rows)