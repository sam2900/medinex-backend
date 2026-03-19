from __future__ import annotations

from pathlib import Path

from src.chunking import build_chunks
from src.pdf_ingest import extract_pdf_pages
from src.retrieval import LocalTfidfRetriever

from src.table1_budget_estimation import extract_table1_budget_estimation
from src.table2_study_details import extract_table2_study_details
from src.table3_visit_details import extract_table3_visit_details
from src.table4_procedures import extract_table4_procedures
from src.table5_non_procedures import extract_table5_non_procedures
from src.table6_site_fees import extract_table6_site_fees
from src.table7_conditional_procedures import extract_table7_conditional_procedures
from src.table8_patient_costs import extract_table8_patient_costs
from src.excel_exporter import export_all_tables_to_excel


def run_protocol_pipeline(
    pdf_path: str | Path,
    output_dir: str | Path,
    use_llm: bool = True,
    top_k: int = 18,
) -> dict:
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = extract_pdf_pages(pdf_path)
    chunks = build_chunks(
        pdf_name=pdf_path.name,
        pages=pages,
        target_words=180,
        overlap_words=40,
    )
    retriever = LocalTfidfRetriever(chunks)

    table1 = extract_table1_budget_estimation(
        pdf_name=pdf_path.name,
        retriever=retriever,
        top_k=top_k,
        use_llm_fallback=use_llm,
    )

    table2 = extract_table2_study_details(
        pdf_name=pdf_path.name,
        retriever=retriever,
        top_k=top_k,
        use_llm_fallback=use_llm,
    )

    table3 = extract_table3_visit_details(
        pdf_name=pdf_path.name,
        retriever=retriever,
        top_k=top_k,
        use_llm_fallback=use_llm,
    )

    table4 = extract_table4_procedures(
        pdf_name=pdf_path.name,
        retriever=retriever,
        table3=table3,
        top_k=top_k,
        use_llm_fallback=use_llm,
    )

    table5 = extract_table5_non_procedures(
        pdf_name=pdf_path.name,
        table3=table3,
    )

    table6 = extract_table6_site_fees(
        pdf_name=pdf_path.name,
    )

    table7 = extract_table7_conditional_procedures(
        pdf_name=pdf_path.name,
        table4=table4,
    )

    table8 = extract_table8_patient_costs(
        pdf_name=pdf_path.name,
    )

    excel_path = output_dir / f"{pdf_path.stem}_budget.xlsx"
    export_all_tables_to_excel(
        output_path=str(excel_path),
        table1=table1,
        table2=table2,
        table3=table3,
        table4=table4,
        table5=table5,
        table6=table6,
        table7=table7,
        table8=table8,
    )

    return {
        "pdf_name": pdf_path.name,
        "table1": table1.model_dump(),
        "table2": table2.model_dump(),
        "table3": table3.model_dump(),
        "table4": table4.model_dump(),
        "table5": table5.model_dump(),
        "table6": table6.model_dump(),
        "table7": table7.model_dump(),
        "table8": table8.model_dump(),
        "excel_path": str(excel_path),
    }