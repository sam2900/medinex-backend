from __future__ import annotations

from typing import List

from .schemas import (
    Table3VisitDetails,
    Table5NonProcedureDetails,
    Table5NonProcedureRow,
)


FIXED_NON_PROCEDURES = [
    "Study Coordinator / CRC (Simple)",
    "Study Coordinator / CRC (Complex)",
    "Physician / PI (Simple)",
    "Physician / PI (Complex)",
    "EDC/CRF entry and upload (staff labor)",
]


def _blank_visit_values(visit_columns: List[str]) -> dict[str, str]:
    return {col: "" for col in visit_columns}


def extract_table5_non_procedures(
    pdf_name: str,
    table3: Table3VisitDetails,
) -> Table5NonProcedureDetails:
    visit_columns = list(dict.fromkeys([v.visit_id for v in table3.visits]))

    rows: List[Table5NonProcedureRow] = []

    for item in FIXED_NON_PROCEDURES:
        rows.append(
            Table5NonProcedureRow(
                non_procedure_item=item,
                code="",
                unit_basis="Per Hour",
                budget="",
                visit_values=_blank_visit_values(visit_columns),
            )
        )

    # spacer rows
        rows.append(
            Table5NonProcedureRow(
                non_procedure_item="",
                code="",
                unit_basis="",
                budget="",
                visit_values=_blank_visit_values(visit_columns),
            )
        )
    rows.append(
        Table5NonProcedureRow(
            non_procedure_item="",
            code="",
            unit_basis="",
            budget="",
            visit_values=_blank_visit_values(visit_columns),
        )
    )

    # footer rows
    footer_labels = [
        "Non Procedures Sub Total",
        "Site Administrative Overhead (OH)",
        "Total Cost Per Visit incl. Overhead",
        "Total Cost Per Subject",
    ]

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