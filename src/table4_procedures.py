from __future__ import annotations

from typing import Dict, List

from .llm_client import AzureOpenAIJsonClient
from .llm_table4 import extract_table4_with_llm
from .retrieval import LocalTfidfRetriever
from .schemas import (
    FieldEvidence,
    Table3VisitDetails,
    Table4ProcedureDetails,
    Table4ProcedureRow,
)


TABLE4_QUERY = (
    "schedule of activities soa appendix schedule of activities "
    "study assessments procedures laboratory physical examination vital signs "
    "hematology chemistry ecg informed consent medical history inclusion exclusion "
    "concomitant medication pk biomarkers imaging mri ct"
)


def debug_table4_retrieval(
    pdf_name: str,
    retriever: LocalTfidfRetriever,
    top_k: int = 18,
) -> Dict:
    matches = retriever.search(TABLE4_QUERY, top_k=top_k)
    field = FieldEvidence(
        field_name="table4_procedures",
        query=TABLE4_QUERY,
        matches=matches,
    )
    return {
        "pdf_name": pdf_name,
        "fields": [field.model_dump()],
    }


def _normalize_procedure_name(value: str) -> str:
    v = " ".join((value or "").split()).strip()
    vl = v.lower()

    if not v:
        return ""

    if "participant identification card" in vl:
        return "Participant Identification Card"

    if "screening number" in vl:
        return "Screening Number Assignment"

    if "inclusion/exclusion" in vl or "eligibility criteria" in vl:
        return "Inclusion/Exclusion Criteria"

    if "demographic" in vl:
        return "Demographics"

    if "medical history" in vl:
        return "Medical History"

    if "prior/concomitant medication" in vl or "concomitant medication" in vl:
        return "Prior/Concomitant Medication Review"

    if "treatment assignment" in vl or "randomization" in vl:
        return "Treatment Asssignment or Randomization"

    if "administration of nmba" in vl:
        return "Administration of NMBA"

    if "administration of study treatment" in vl:
        return "Administration of Study Treatment"

    if "extubation readiness" in vl:
        return "Extubation Readiness Assessment"

    if "neuromuscular monitoring" in vl:
        return "Neuromuscular Monitoring"

    if "full physical examination" in vl:
        return "Full Physical Examination"

    if "targeted physical examination" in vl:
        return "Targeted Physical Examination"

    if "physical examination" in vl:
        return "Physical Examination"

    if "vital signs" in vl:
        return "Vital Signs"

    if "height" in vl and "weight" in vl:
        return "Height/weight/BMI workflow"

    if "ecog" in vl:
        return "ECOG Performance Status"

    if "continuous heart rate monitoring" in vl:
        return "Continuous Heart Rate Monitoring (ECG)"

    if v == "ECG" or "electrocardiogram" in vl:
        return "Electrocardiogram"

    if "hematology" in vl:
        return "Hematology"

    if "coagulation" in vl:
        return "Coagulation"

    if "chemistry" in vl:
        return "Chemistry"

    if "urinalysis" in vl:
        return "Urinalysis, dipstick"

    if "mandatory laboratory" in vl:
        return "Additional Mandatory laboratory"

    if "plasma pk" in vl or "pharmacokinetic" in vl:
        return "Plasma PK Sample (2 mL)"

    if "plasma biomarker" in vl or ("biomarker" in vl and "plasma" in vl):
        return "Plasma Biomarkers (10 mL)"

    if "tumor tissue" in vl:
        return "Tumor Tissue Sample"

    if "ae/sae/eci" in vl or ("adverse event" in vl and "review" in vl):
        return "AE/SAE/ECI review"

    if "adverse device" in vl:
        return "Adverse Device Event Monitoring"

    if "eq-5d" in vl:
        return "EQ-5D administration"

    if "qlq" in vl:
        return "INT-QLQC-64"

    # imaging normalization
    if "imaging work" in vl:
        return "MRI or CT Brain"

    if "disease assessment" in vl and "ct" in vl:
        return "MRI or CT Brain"

    if "mri" in vl or "ct brain" in vl:
        return "MRI or CT Brain"

    return v


def _normalize_unit_basis(value: str) -> str:
    v = " ".join((value or "").split()).strip().lower()

    if v == "per procedure":
        return "Per Procedure"
    if v == "per assessment":
        return "Per Assessment"

    return value.strip() if value else ""


def _blank_visit_values(visit_columns: List[str]) -> dict[str, str]:
    return {col: "" for col in visit_columns}


def _normalize_visit_marker(value: str) -> str:
    marker = " ".join((value or "").split()).strip()
    if not marker:
        return ""

    marker_l = marker.lower()
    if marker_l in {"x", "yes", "y", "1", "true"}:
        return "X"

    return marker


def _normalize_visit_values(raw_values: dict, visit_columns: List[str]) -> dict[str, str]:
    normalized = _blank_visit_values(visit_columns)

    for visit_id in visit_columns:
        normalized[visit_id] = _normalize_visit_marker(str((raw_values or {}).get(visit_id, "")))

    return normalized


def _dedupe_preserve_order(rows: List[Table4ProcedureRow]) -> List[Table4ProcedureRow]:
    seen: dict[str, Table4ProcedureRow] = {}
    order: List[str] = []

    for row in rows:
        key = row.procedure.strip().lower()
        if not key:
            continue

        if key in seen:
            existing = seen[key]
            for visit_id, marker in (row.visit_values or {}).items():
                if _normalize_visit_marker(marker):
                    existing.visit_values[visit_id] = _normalize_visit_marker(marker)
            continue
        seen[key] = row
        order.append(key)

    return [seen[key] for key in order]


def _split_special_rows(rows: List[Table4ProcedureRow], visit_columns: List[str]) -> List[Table4ProcedureRow]:
    out: List[Table4ProcedureRow] = []

    for row in rows:
        if row.procedure == "Clinical Safety Laboratory Assessments":
            out.append(
                Table4ProcedureRow(
                    procedure="Hematology",
                    code="",
                    unit_basis="Per Procedure",
                    budget="",
                    visit_values=dict(row.visit_values or _blank_visit_values(visit_columns)),
                )
            )
            out.append(
                Table4ProcedureRow(
                    procedure="Chemistry",
                    code="",
                    unit_basis="Per Assessment",
                    budget="",
                    visit_values=dict(row.visit_values or _blank_visit_values(visit_columns)),
                )
            )
            continue

        out.append(row)

    return out


def _remove_non_budget_rows(rows: List[Table4ProcedureRow]) -> List[Table4ProcedureRow]:
    exclude = {
        "Subsequent Anticancer Therapy Status",
        "Survival Status",
    }
    return [r for r in rows if r.procedure not in exclude]


def _ensure_core_rows(rows: List[Table4ProcedureRow], visit_columns: List[str]) -> List[Table4ProcedureRow]:
    core_rows = [
        "Participant Identification Card",
        "Screening Number Assignment",
        "Inclusion/Exclusion Criteria",
    ]

    existing = {r.procedure for r in rows}
    inserts: List[Table4ProcedureRow] = []

    for name in core_rows:
        if name not in existing:
            inserts.append(
                Table4ProcedureRow(
                    procedure=name,
                    code="",
                    unit_basis="Per Assessment",
                    budget="",
                    visit_values=_blank_visit_values(visit_columns),
                )
            )

    return inserts + rows


def _enforce_canonical_order(rows: List[Table4ProcedureRow]) -> List[Table4ProcedureRow]:
    order = [
        "Informed Consent",
        "Participant Identification Card",
        "Screening Number Assignment",
        "Inclusion/Exclusion Criteria",
        "Demographics",
        "Medical History",
        "Prior/Concomitant Medication Review",
        "Treatment Asssignment or Randomization",
        "Administration of NMBA",
        "Administration of Study Treatment",
        "Extubation Readiness Assessment",
        "Neuromuscular Monitoring",
        "Full Physical Examination",
        "Targeted Physical Examination",
        "Physical Examination",
        "Vital Signs",
        "Height/weight/BMI workflow",
        "ECOG Performance Status",
        "Continuous Heart Rate Monitoring (ECG)",
        "Electrocardiogram",
        "Hematology",
        "Coagulation",
        "Chemistry",
        "Urinalysis, dipstick",
        "Additional Mandatory laboratory",
        "MRI or CT Brain",
        "Plasma PK Sample (2 mL)",
        "Plasma Biomarkers (10 mL)",
        "Tumor Tissue Sample",
        "AE/SAE/ECI review",
        "Adverse Device Event Monitoring",
        "EQ-5D administration",
        "INT-QLQC-64",
    ]
    rank = {name: i for i, name in enumerate(order)}
    return sorted(rows, key=lambda r: rank.get(r.procedure, 9999))


def _append_footer_rows(rows, visit_columns):
    subtotal = Table4ProcedureRow(
        procedure="Procedures Sub-Total",
        code="",
        unit_basis="",
        budget="",
        visit_values=_blank_visit_values(visit_columns),
    )
    rows.append(subtotal)
    return rows


def extract_table4_procedures(
    pdf_name: str,
    retriever: LocalTfidfRetriever,
    table3: Table3VisitDetails,
    top_k: int = 18,
    use_llm_fallback: bool = True,
) -> Table4ProcedureDetails:
    visit_columns = list(dict.fromkeys([v.visit_id for v in table3.visits]))

    matches = retriever.search(TABLE4_QUERY, top_k=top_k)

    if not use_llm_fallback:
        rows = _append_footer_rows([], visit_columns)
        return Table4ProcedureDetails(
            pdf_name=pdf_name,
            visit_columns=visit_columns,
            procedures=rows,
        )

    client = AzureOpenAIJsonClient()
    data = extract_table4_with_llm(
        matches=matches,
        visit_columns=visit_columns,
        client=client,
    )

    raw_rows = data.get("procedures", []) or []
    rows: List[Table4ProcedureRow] = []

    for item in raw_rows:
        procedure = _normalize_procedure_name(str(item.get("procedure", "")).strip())
        if not procedure:
            continue

        unit_basis = _normalize_unit_basis(str(item.get("unit_basis", "")).strip())

        rows.append(
            Table4ProcedureRow(
                procedure=procedure,
                code="",
                unit_basis=unit_basis,
                budget="",
                visit_values=_normalize_visit_values(item.get("visit_values", {}) or {}, visit_columns),
            )
        )

    cleaned_rows: List[Table4ProcedureRow] = []
    for row in rows:
        if row.procedure.strip().lower() == "procedures sub-total":
            continue
        cleaned_rows.append(row)

    cleaned_rows = _split_special_rows(cleaned_rows, visit_columns)
    cleaned_rows = _dedupe_preserve_order(cleaned_rows)
    cleaned_rows = _remove_non_budget_rows(cleaned_rows)
    cleaned_rows = _ensure_core_rows(cleaned_rows, visit_columns)
    cleaned_rows = _enforce_canonical_order(cleaned_rows)
    cleaned_rows = _append_footer_rows(cleaned_rows, visit_columns)

    return Table4ProcedureDetails(
        pdf_name=pdf_name,
        visit_columns=visit_columns,
        procedures=cleaned_rows,
    )
