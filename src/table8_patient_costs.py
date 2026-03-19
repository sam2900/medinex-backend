from __future__ import annotations

from typing import List

from .schemas import Table8PatientCostDetails, Table8PatientCostRow


FIXED_PATIENT_COST_ROWS = [
    ("Patient Travel Reimbursement", "Per Visit"),
    ("Patient Meals / Refreshments", "Per Visit"),
    ("Patient Overnight Stay (Hotel)", "Per Night"),
    ("Patient Parking / Local Transport", "Per Visit"),
    ("Patient Stipend / Inconvenience Fee", "Per Visit"),
    ("Patient Reimbursement – Overnight Stay", "Per Visit"),
    ("Family/Caregiver Travel Support", "Per Visit"),
    ("Family/Caregiver Meals", "Per Visit"),
    ("Patient Miscellaneous Expenses", "Per Visit / Lump"),
]


def extract_table8_patient_costs(pdf_name: str) -> Table8PatientCostDetails:
    rows: List[Table8PatientCostRow] = []

    for item_name, unit_basis in FIXED_PATIENT_COST_ROWS:
        rows.append(
            Table8PatientCostRow(
                patient_cost_item=item_name,
                code="",
                unit_basis=unit_basis,
                unit_cost="",
            )
        )

    return Table8PatientCostDetails(
        pdf_name=pdf_name,
        items=rows,
    )