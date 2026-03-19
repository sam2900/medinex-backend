from __future__ import annotations

from typing import List

from .schemas import Table6SiteFeeDetails, Table6SiteFeeRow


FIXED_SITE_FEE_ROWS = [
    ("Site Start-Up / Activation Fee", "One-time"),
    ("Ethics / IRB Submission (Initial)", "One-time"),
    ("Ethics / IRB Amendment Review", "Per Amendment"),
    ("Ethics / IRB Annual Review", "Annual"),
    ("Protocol Amendment Processing - Simple", "Per Amendment"),
    ("Protocol Amendment Processing - Complex", "Per Amendment"),
    ("Site Initiation Visit fee", "One-time"),
    ("Investigator Meeting Participation", "Per Meeting"),
    ("Site Staff Training", "One-time / Hourly"),
    ("Pharmacy Set-Up (Study Preparation)", "One-time"),
    ("Ongoing Pharmacy Support / Maintenance", "Annual"),
    ("Pharmacy Study Close-Out", "One-time"),
    ("Archiving & Records Storage", "Per Box"),
    ("Archiving & Records Storage", "Annual / One-time"),
    ("Site Close-Out Administration", "One-time"),
    ("Regulatory Document Preparation (Initial)", "One-time"),
    ("Regulatory Document Preparation (Updates)", "Per Amendment"),
    ("Audit Preparation / Support", "Per Audit"),
    ("Investigator Protocol Review / Oversight", "One-time"),
    ("Pharmacy Drug Receipt & Accountability", "Per Shipment/Batch"),
    ("EDC / System Access Fee", "Per Occurrence"),
    ("Administrative Fee", "Annual/One-time"),
    ("Department Set-Up Fee (Lab, Radiology, Nuclear Medicine etc.)", "One-time"),
    ("Chart review fee", "Per Chart"),
    ("Advertising/Recruitment Fee", "One-time"),
    ("Budget & Contract Negotiation fee", "One-time"),
]


def extract_table6_site_fees(pdf_name: str) -> Table6SiteFeeDetails:
    rows: List[Table6SiteFeeRow] = []

    for description, unit_basis in FIXED_SITE_FEE_ROWS:
        rows.append(
            Table6SiteFeeRow(
                site_fee_description=description,
                code="",
                unit_basis=unit_basis,
                unit_cost="",
            )
        )

    return Table6SiteFeeDetails(
        pdf_name=pdf_name,
        items=rows,
    )