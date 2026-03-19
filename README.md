# Protocol Budget POC

Starter code for a scalable protocol-to-template extraction pipeline.

## What this version does
- Reads a protocol PDF page by page
- Chunks the text into reusable semantic chunks
- Runs a retrieval step for Table #2 study-detail fields
- Writes a debug JSON file with top candidate evidence
- Creates a placeholder structured JSON for Table #2

## Suggested workflow
1. Put your PDFs into `inputs/`
2. Put the Excel template into `inputs/`
3. Run:
   ```bash
   python main.py --pdf "inputs/Protocol 001_ClinicalTrialgov_NCT04644315.pdf" --mode debug_table2
   ```
4. Review the generated files in `outputs/`

## Current design choices
- Retrieval uses a local TF-IDF baseline first so the POC is easy to run in VS Code.
- The extractor is retrieval-first, not page-location-first.
- Excel writing is stubbed but separated from extraction logic.

## Next steps
- Improve field extraction rules for Table #2
- Add LLM fallback only when deterministic extraction is uncertain
- Add Excel write mapping once Table #2 JSON looks stable across the 5 PDFs
