from __future__ import annotations

import json
from typing import List, Optional

from .llm_client import AzureOpenAIJsonClient


def _serialize(matches: List, max_chars: int = 1800) -> list[dict]:
    out = []
    for m in matches:
        out.append(
            {
                "chunk_id": getattr(m, "chunk_id", None),
                "page_num": getattr(m, "page_num", None),
                "score": getattr(m, "score", None),
                "text": (getattr(m, "text", "") or "")[:max_chars],
            }
        )
    return out


def classify_table7_with_llm(
    table4_rows: List[dict],
    matches: List,
    client: Optional[AzureOpenAIJsonClient] = None,
) -> dict:
    client = client or AzureOpenAIJsonClient()

    system_prompt = """
You build a protocol-specific Conditional Procedures table for a clinical trial budget.
Return ONLY valid JSON.
You must start from the provided Table 4 rows and use the protocol evidence to decide which rows belong in Table 7.
Do not invent rows from other protocols.
""".strip()

    user_prompt = f"""
Build Table #7: Conditional Procedures.

Important definition:
- Start from the normalized Table 4 procedure list for THIS SAME protocol.
- Table 7 should include rows from Table 4 that are conditional, optional, imaging-driven,
  PK/biomarker/tissue-sampling related, special-handling, footnote-driven, or otherwise
  treated outside the standard recurring visit schedule.
- You may also add a few extra rows if clearly supported by the protocol evidence.

Rules:
1. Prefer selecting rows from Table 4 rather than rewriting them.
2. Only include a Table 4 row if supported by THIS protocol's evidence.
3. Add extra rows only if they are clearly supported and not already represented by a Table 4 row.
4. For extra rows, infer unit_basis as one of:
   - Per Assessment
   - Per Procedure
   - Per Timepoint
   - Per Hour
5. Do not return duplicates.
6. Do not return footer rows.

Return JSON exactly like this:
{{
  "include_from_table4": [
    "MRI or CT Brain",
    "Plasma PK Sample (2 mL)"
  ],
  "extra_rows": [
    {{
      "procedure": "PK timed timepoint coordination (windows)",
      "unit_basis": "Per Timepoint"
    }}
  ]
}}

Table 4 rows for this protocol:
{json.dumps(table4_rows, indent=2)}

Protocol evidence:
{json.dumps(_serialize(matches), indent=2)}
""".strip()

    return client.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
    )