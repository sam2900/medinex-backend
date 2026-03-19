from typing import List
from .schemas import Table7ConditionalProcedureDetails, Table7ConditionalProcedureRow


EXCLUDE_ALWAYS = {
    "procedures sub-total",
}


def should_include(proc_name: str) -> bool:
    name = (proc_name or "").strip().lower()
    if not name:
        return False
    if name in EXCLUDE_ALWAYS:
        return False
    return True


def extract_table7_conditional_procedures(
    pdf_name: str,
    table4,
) -> Table7ConditionalProcedureDetails:

    items: List[Table7ConditionalProcedureRow] = []

    for proc in table4.procedures:
        name = (proc.procedure or "").strip()

        if not should_include(name):
            continue

        items.append(
            Table7ConditionalProcedureRow(
                conditional_procedure=name,
                code="",
                unit_basis=proc.unit_basis or "Per Assessment",
                unit_cost="",
                overhead="",
                unit_cost_incl_overhead="",
            )
        )

    seen = set()
    deduped = []
    for i in items:
        key = i.conditional_procedure.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(i)

    return Table7ConditionalProcedureDetails(
        pdf_name=pdf_name,
        items=deduped,
    )


def debug_table7_trace(pdf_name: str, table4):
    return {
        "pdf_name": pdf_name,
        "input_table4_procedures": [
            {
                "procedure": p.procedure,
                "unit_basis": p.unit_basis,
            }
            for p in table4.procedures
        ],
        "selected": [
            p.procedure
            for p in table4.procedures
            if should_include(p.procedure or "")
        ],
    }