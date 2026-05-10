from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.chunking import build_chunks
from src.excel_writer import save_table2_json
from src.pdf_ingest import extract_pdf_pages
from src.retrieval import LocalTfidfRetriever

from src.table1_budget_estimation import debug_table1_retrieval, extract_table1_budget_estimation
from src.table2_study_details import debug_table2_retrieval, extract_table2_study_details
from src.table3_visit_details import debug_table3_retrieval, debug_table3_trace, extract_table3_visit_details
from src.table4_procedures import debug_table4_retrieval, extract_table4_procedures
from src.table5_non_procedures import extract_table5_non_procedures
from src.table6_site_fees import extract_table6_site_fees
from src.table7_conditional_procedures import debug_table7_trace, extract_table7_conditional_procedures
from src.table8_patient_costs import extract_table8_patient_costs

from src.source_selector import (
    debug_source_selector_retrieval,
    debug_source_selector_trace,
    select_protocol_source,
)

from src.excel_exporter import export_all_tables_to_excel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Protocol budget extraction POC")
    parser.add_argument("--pdf", required=True, help="Path to protocol PDF")
    parser.add_argument("--template", required=False, help="Unused for now; Excel is generated from scratch")
    parser.add_argument(
        "--mode",
        choices=[
            "debug_table1",
            "extract_table1",
            "debug_table2",
            "extract_table2",
            "debug_table3",
            "debug_table3_trace",
            "extract_table3",
            "debug_table4",
            "extract_table4",
            "extract_table5",
            "extract_table6",
            "debug_table7",
            "extract_table7",
            "extract_table8",
            "debug_source_selector",
            "debug_source_selector_trace",
            "export_excel",
        ],
        default="debug_table2",
        help="Pipeline mode",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for debug and result files",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Enable Azure OpenAI fallback",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=18,
        help="Number of retrieved chunks",
    )
    return parser.parse_args()


def print_and_save_table(name: str, table_obj, output_dir: Path) -> None:
    print(f"\n===== {name} =====")

    try:
        data = table_obj.model_dump()
    except Exception:
        data = str(table_obj)

    preview = json.dumps(data, indent=2, ensure_ascii=False)
    print(preview[:2000])

    file_path = output_dir / f"{name.lower().replace(' ', '_')}.json"
    file_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved → {file_path}")


def main() -> None:
    args = parse_args()

    pdf_path = Path(args.pdf)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = extract_pdf_pages(pdf_path)
    chunks = build_chunks(
        pdf_name=pdf_path.name,
        pages=pages,
        target_words=180,
        overlap_words=40,
    )

    retriever = LocalTfidfRetriever(chunks)

    if args.mode == "debug_table1":
        debug_payload = debug_table1_retrieval(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
        )
        debug_path = output_dir / f"{pdf_path.stem}_table1_debug.json"
        debug_path.write_text(
            json.dumps(debug_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved debug retrieval output: {debug_path}")
        return

    if args.mode == "extract_table1":
        table1 = extract_table1_budget_estimation(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )
        result_path = output_dir / f"{pdf_path.stem}_table1_result.json"
        result_path.write_text(
            table1.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"Saved structured Table #1 output: {result_path}")
        return

    if args.mode == "debug_table2":
        debug_payload = debug_table2_retrieval(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
        )
        debug_path = output_dir / f"{pdf_path.stem}_table2_debug.json"
        debug_path.write_text(
            json.dumps(debug_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved debug retrieval output: {debug_path}")
        return

    if args.mode == "extract_table2":
        table2 = extract_table2_study_details(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )
        result_path = output_dir / f"{pdf_path.stem}_table2_result.json"
        save_table2_json(table2, result_path)
        print(f"Saved structured Table #2 output: {result_path}")
        return

    if args.mode == "debug_source_selector":
        debug_payload = debug_source_selector_retrieval(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
        )
        debug_path = output_dir / f"{pdf_path.stem}_source_selector_debug.json"
        debug_path.write_text(
            json.dumps(debug_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved debug retrieval output: {debug_path}")
        return

    if args.mode == "debug_source_selector_trace":
        debug_payload = debug_source_selector_trace(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
        )
        debug_path = output_dir / f"{pdf_path.stem}_source_selector_trace.json"
        debug_path.write_text(
            json.dumps(debug_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved debug trace output: {debug_path}")
        return

    if args.mode == "debug_table3":
        debug_payload = debug_table3_retrieval(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
        )
        debug_path = output_dir / f"{pdf_path.stem}_table3_debug.json"
        debug_path.write_text(
            json.dumps(debug_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved debug retrieval output: {debug_path}")
        return

    if args.mode == "debug_table3_trace":
        debug_payload = debug_table3_trace(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
        )
        debug_path = output_dir / f"{pdf_path.stem}_table3_trace.json"
        debug_path.write_text(
            json.dumps(debug_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved debug trace output: {debug_path}")
        return

    if args.mode == "extract_table3":
        table3 = extract_table3_visit_details(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )
        result_path = output_dir / f"{pdf_path.stem}_table3_result.json"
        result_path.write_text(
            table3.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"Saved structured Table #3 output: {result_path}")
        return

    if args.mode == "debug_table4":
        debug_payload = debug_table4_retrieval(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
        )
        debug_path = output_dir / f"{pdf_path.stem}_table4_debug.json"
        debug_path.write_text(
            json.dumps(debug_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved debug retrieval output: {debug_path}")
        return

    if args.mode == "extract_table4":
        table3 = extract_table3_visit_details(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )

        table4 = extract_table4_procedures(
            pdf_name=pdf_path.name,
            retriever=retriever,
            table3=table3,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )

        result_path = output_dir / f"{pdf_path.stem}_table4_result.json"
        result_path.write_text(
            table4.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"Saved structured Table #4 output: {result_path}")
        return

    if args.mode == "extract_table5":
        table3 = extract_table3_visit_details(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )

        table4 = extract_table4_procedures(
            pdf_name=pdf_path.name,
            retriever=retriever,
            table3=table3,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )

        table5 = extract_table5_non_procedures(
            pdf_name=pdf_path.name,
            table3=table3,
            table4=table4,
        )

        result_path = output_dir / f"{pdf_path.stem}_table5_result.json"
        result_path.write_text(
            table5.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"Saved structured Table #5 output: {result_path}")
        return

    if args.mode == "extract_table6":
        table6 = extract_table6_site_fees(
            pdf_name=pdf_path.name,
        )

        result_path = output_dir / f"{pdf_path.stem}_table6_result.json"
        result_path.write_text(
            table6.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"Saved structured Table #6 output: {result_path}")
        return

    if args.mode == "debug_table7":
        table3 = extract_table3_visit_details(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )

        table4 = extract_table4_procedures(
            pdf_name=pdf_path.name,
            retriever=retriever,
            table3=table3,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )

        debug_payload = debug_table7_trace(
            pdf_name=pdf_path.name,
            table4=table4,

        )

        debug_path = output_dir / f"{pdf_path.stem}_table7_debug.json"
        debug_path.write_text(
            json.dumps(debug_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved debug retrieval output: {debug_path}")
        return

    if args.mode == "extract_table7":
        table3 = extract_table3_visit_details(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )

        table4 = extract_table4_procedures(
            pdf_name=pdf_path.name,
            retriever=retriever,
            table3=table3,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )

        table7 = extract_table7_conditional_procedures(
            pdf_name=pdf_path.name,
            table4=table4,
        )

        result_path = output_dir / f"{pdf_path.stem}_table7_result.json"
        result_path.write_text(
            table7.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"Saved structured Table #7 output: {result_path}")
        return

    if args.mode == "extract_table8":
        table8 = extract_table8_patient_costs(
            pdf_name=pdf_path.name,
        )

        result_path = output_dir / f"{pdf_path.stem}_table8_result.json"
        result_path.write_text(
            table8.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"Saved structured Table #8 output: {result_path}")
        return

    if args.mode == "export_excel":
        table1 = extract_table1_budget_estimation(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )
        print_and_save_table("Table1", table1, output_dir)

        table2 = extract_table2_study_details(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )
        print_and_save_table("Table2", table2, output_dir)

        table3 = extract_table3_visit_details(
            pdf_name=pdf_path.name,
            retriever=retriever,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )
        print_and_save_table("Table3", table3, output_dir)

        table4 = extract_table4_procedures(
            pdf_name=pdf_path.name,
            retriever=retriever,
            table3=table3,
            top_k=args.top_k,
            use_llm_fallback=args.use_llm,
        )
        print_and_save_table("Table4", table4, output_dir)

        table5 = extract_table5_non_procedures(
            pdf_name=pdf_path.name,
            table3=table3,
            table4=table4,
        )
        print_and_save_table("Table5", table5, output_dir)

        table6 = extract_table6_site_fees(
            pdf_name=pdf_path.name,
        )
        print_and_save_table("Table6", table6, output_dir)

        table7 = extract_table7_conditional_procedures(
            pdf_name=pdf_path.name,
            table4=table4,
        )
        print_and_save_table("Table7", table7, output_dir)

        table8 = extract_table8_patient_costs(
            pdf_name=pdf_path.name,
        )
        print_and_save_table("Table8", table8, output_dir)

        output_file = output_dir / f"{pdf_path.stem}_budget.xlsx"

        export_all_tables_to_excel(
            output_path=str(output_file),
            table1=table1,
            table2=table2,
            table3=table3,
            table4=table4,
            table5=table5,
            table6=table6,
            table7=table7,
            table8=table8,
        )

        print(f"\nSaved Excel output: {output_file}")
        return


if __name__ == "__main__":
    main()
