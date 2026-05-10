from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .schemas import (
    Table3VisitDetails,
    Table4ProcedureDetails,
    Table5NonProcedureDetails,
    Table5NonProcedureRow,
)


ALWAYS_INCLUDED_NON_PROCEDURES = [
    ("INT-NP-001", "Study Coordinator / CRC (Simple)"),
    ("INT-NP-002", "Study Coordinator / CRC (Complex)"),
    ("INT-NP-003", "Physician / PI (Simple)"),
    ("INT-NP-004", "Physician / PI (Complex)"),
    ("INT-NP-026", "EDC/CRF Entry and Upload"),
]

CONDITIONAL_NON_PROCEDURES = [
    ("INT-NP-033", "IP Dispensing Support (Staff Labor)"),
]

SCREENING_KEYWORDS = ("screening", "screen")
BASELINE_KEYWORDS = ("baseline", "day 1", "pre-dose", "predose", "randomization")
EOT_KEYWORDS = ("end of treatment", "eot", "treatment discontinuation", "end-of-treatment")
TELEPHONE_KEYWORDS = ("telephone", "phone", "call", "televisit", "tele-visit", "follow-up contact")
DRUG_ADMIN_KEYWORDS = (
    "administration of study treatment",
    "administration of nmba",
    "administration",
    "study treatment",
    "drug administration",
    "investigational medicinal product",
    "dosing",
    "infusion",
    "injection",
    "inject",
    "oral dosing",
    "iv",
    "sc",
    "im",
    "subcutaneous",
    "intramuscular",
    "intravenous",
)
COMPLEX_DRUG_ADMIN_KEYWORDS = (
    "chemotherapy",
    "infusion",
    "intravenous",
    "iv",
)


@dataclass
class VisitContext:
    visit_id: str
    visit_title: str
    visit_index: int
    procedure_names: List[str]
    procedure_count: int
    has_drug_administration: bool
    has_complex_drug_administration: bool


def _blank_visit_values(visit_columns: List[str]) -> dict[str, str]:
    return {col: "" for col in visit_columns}


def _normalize_text(value: str) -> str:
    return " ".join((value or "").split()).strip().lower()


def _has_any_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _is_truthy_visit_marker(value: str) -> bool:
    marker = _normalize_text(value)
    return marker not in {"", "0", "false", "no", "n"}


def _format_hours(value: float) -> str:
    if value.is_integer():
        return f"{value:.1f}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _visit_text(title: str, visit_id: str) -> str:
    return f"{title} {visit_id}".strip().lower()


def _is_screening_visit(title: str, visit_id: str, visit_index: int) -> bool:
    text = _visit_text(title, visit_id)
    return visit_index == 0 or _has_any_keyword(text, SCREENING_KEYWORDS)


def _is_baseline_visit(title: str, visit_id: str, visit_index: int, seen_screening: bool) -> bool:
    text = _visit_text(title, visit_id)
    if not seen_screening and visit_index != 0:
        return False
    if _is_screening_visit(title, visit_id, visit_index):
        return False
    return _has_any_keyword(text, BASELINE_KEYWORDS)


def _is_eot_visit(title: str, visit_id: str) -> bool:
    return _has_any_keyword(_visit_text(title, visit_id), EOT_KEYWORDS)


def _is_telephone_visit(ctx: VisitContext) -> bool:
    visit_text = _visit_text(ctx.visit_title, ctx.visit_id)
    if _has_any_keyword(visit_text, TELEPHONE_KEYWORDS):
        return True

    procedure_blob = " ".join(ctx.procedure_names).lower()
    return "telephone" in procedure_blob or "phone" in procedure_blob


def _is_complex_interim_visit(ctx: VisitContext) -> bool:
    return ctx.procedure_count > 7 or ctx.has_complex_drug_administration


def _is_footer_procedure(procedure_name: str) -> bool:
    return _normalize_text(procedure_name) in {"procedures sub-total"}


def _has_drug_administration(procedure_name: str) -> bool:
    procedure_text = _normalize_text(procedure_name)
    return any(keyword in procedure_text for keyword in DRUG_ADMIN_KEYWORDS)


def _has_complex_drug_administration(procedure_name: str) -> bool:
    procedure_text = _normalize_text(procedure_name)
    return any(keyword in procedure_text for keyword in COMPLEX_DRUG_ADMIN_KEYWORDS)


def _build_visit_contexts(
    table3: Table3VisitDetails,
    table4: Table4ProcedureDetails,
) -> List[VisitContext]:
    contexts: List[VisitContext] = []

    for visit_index, visit in enumerate(table3.visits):
        procedure_names: List[str] = []
        has_drug_administration = False
        has_complex_drug_administration = False

        for procedure_row in table4.procedures:
            procedure_name = procedure_row.procedure.strip()
            if not procedure_name or _is_footer_procedure(procedure_name):
                continue

            marker = (procedure_row.visit_values or {}).get(visit.visit_id, "")
            if not _is_truthy_visit_marker(marker):
                continue

            procedure_names.append(procedure_name)
            has_drug_administration = has_drug_administration or _has_drug_administration(procedure_name)
            has_complex_drug_administration = (
                has_complex_drug_administration or _has_complex_drug_administration(procedure_name)
            )

        contexts.append(
            VisitContext(
                visit_id=visit.visit_id,
                visit_title=visit.visit_title,
                visit_index=visit_index,
                procedure_names=procedure_names,
                procedure_count=len(procedure_names),
                has_drug_administration=has_drug_administration,
                has_complex_drug_administration=has_complex_drug_administration,
            )
        )

    return contexts


def _build_row(
    item_label: str,
    code: str,
    unit_basis: str,
    visit_columns: List[str],
) -> Table5NonProcedureRow:
    return Table5NonProcedureRow(
        non_procedure_item=item_label,
        code=code,
        unit_basis=unit_basis,
        budget="",
        visit_values=_blank_visit_values(visit_columns),
    )


def _apply_hours(row_map: Dict[str, Table5NonProcedureRow], code: str, visit_id: str, hours: float) -> None:
    row_map[code].visit_values[visit_id] = _format_hours(hours)


def _classify_and_assign(row_map: Dict[str, Table5NonProcedureRow], contexts: List[VisitContext]) -> None:
    seen_screening = False

    for ctx in contexts:
        if _is_screening_visit(ctx.visit_title, ctx.visit_id, ctx.visit_index):
            _apply_hours(row_map, "INT-NP-002", ctx.visit_id, 3.0)
            _apply_hours(row_map, "INT-NP-004", ctx.visit_id, 2.0)
            _apply_hours(row_map, "INT-NP-026", ctx.visit_id, 1.5)
            seen_screening = True
        elif _is_baseline_visit(ctx.visit_title, ctx.visit_id, ctx.visit_index, seen_screening):
            _apply_hours(row_map, "INT-NP-002", ctx.visit_id, 3.0)
            _apply_hours(row_map, "INT-NP-004", ctx.visit_id, 2.0)
            _apply_hours(row_map, "INT-NP-026", ctx.visit_id, 1.5)
        elif _is_eot_visit(ctx.visit_title, ctx.visit_id):
            _apply_hours(row_map, "INT-NP-002", ctx.visit_id, 3.0)
            _apply_hours(row_map, "INT-NP-004", ctx.visit_id, 2.0)
            _apply_hours(row_map, "INT-NP-026", ctx.visit_id, 1.5)
        elif _is_telephone_visit(ctx):
            _apply_hours(row_map, "INT-NP-001", ctx.visit_id, 0.5)
            _apply_hours(row_map, "INT-NP-026", ctx.visit_id, 0.5)
        else:
            is_complex = _is_complex_interim_visit(ctx)
            _apply_hours(row_map, "INT-NP-001", ctx.visit_id, 3.0 if is_complex else 2.0)
            _apply_hours(row_map, "INT-NP-003", ctx.visit_id, 1.5 if is_complex else 1.0)
            _apply_hours(row_map, "INT-NP-026", ctx.visit_id, 1.0)

        if ctx.has_drug_administration and "INT-NP-033" in row_map:
            _apply_hours(row_map, "INT-NP-033", ctx.visit_id, 1.0)


def _has_any_assigned_values(row: Table5NonProcedureRow) -> bool:
    return any(_is_truthy_visit_marker(value) for value in row.visit_values.values())


def extract_table5_non_procedures(
    pdf_name: str,
    table3: Table3VisitDetails,
    table4: Table4ProcedureDetails,
) -> Table5NonProcedureDetails:
    visit_columns = list(dict.fromkeys([v.visit_id for v in table3.visits]))
    contexts = _build_visit_contexts(table3=table3, table4=table4)

    row_map: Dict[str, Table5NonProcedureRow] = {}
    rows: List[Table5NonProcedureRow] = []

    for code, item_label in ALWAYS_INCLUDED_NON_PROCEDURES:
        row = _build_row(
            item_label=item_label,
            code=code,
            unit_basis="Per Hour",
            visit_columns=visit_columns,
        )
        row_map[code] = row
        rows.append(row)

    for code, item_label in CONDITIONAL_NON_PROCEDURES:
        row = _build_row(
            item_label=item_label,
            code=code,
            unit_basis="Per Hour",
            visit_columns=visit_columns,
        )
        row_map[code] = row

    _classify_and_assign(row_map=row_map, contexts=contexts)

    for code, _ in CONDITIONAL_NON_PROCEDURES:
        conditional_row = row_map[code]
        if _has_any_assigned_values(conditional_row):
            rows.append(conditional_row)

    footer_labels = [
        "Non Procedures Sub Total",
        "Site Administrative Overhead (OH)",
        "Total Cost Per Visit incl. Overhead",
        "Total Cost Per Subject",
    ]

    rows.append(
        Table5NonProcedureRow(
            non_procedure_item="",
            code="",
            unit_basis="",
            budget="",
            visit_values=_blank_visit_values(visit_columns),
        )
    )

    for label in footer_labels:
        rows.append(
            Table5NonProcedureRow(
                non_procedure_item=label,
                code="",
                unit_basis="",
                budget="",
                visit_values=_blank_visit_values(visit_columns),
            )
        )

    return Table5NonProcedureDetails(
        pdf_name=pdf_name,
        visit_columns=visit_columns,
        items=rows,
    )
