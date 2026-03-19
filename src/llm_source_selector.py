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


def select_protocol_source_with_llm(
    matches: List,
    client: Optional[AzureOpenAIJsonClient] = None,
) -> dict:
    client = client or AzureOpenAIJsonClient()

    system_prompt = """
You identify the primary operational schedule source in a clinical trial protocol.
Return ONLY valid JSON.
Use only the provided evidence.
""".strip()

    user_prompt = f"""
Determine the primary source table type for extracting visits/procedures for budgeting.

Valid source_type values:
- "soa_table"
- "summary_table"
- "hybrid"

Definitions:
- soa_table: Appendix / Schedule of Activities style table with visits/cadence/footnotes
- summary_table: summary/evaluation tables that define treatment/EOT/follow-up timing
- hybrid: both are needed, with one primary and one secondary

Return JSON exactly like this:
{{
  "source_type": "soa_table",
  "confidence": "high",
  "primary_tables": [
    {{
      "label": "Appendix 1 Schedule of Activities",
      "page_hint": 115,
      "reason": "contains the primary visit/procedure matrix"
    }}
  ],
  "secondary_tables": [
    {{
      "label": "Table 5 Follow-up Evaluations",
      "page_hint": 73,
      "reason": "contains follow-up timing"
    }}
  ],
  "notes": [
    "string"
  ]
}}

Important rules:
1. Identify the table(s) that should drive budgeting visits/procedures.
2. Prefer the table that explicitly defines operational timing.
3. If treatment and follow-up are split across multiple summary tables, that can still be summary_table.
4. Use hybrid only if both source styles are genuinely needed.
5. Include page hints only if reasonably supported by the evidence.

Protocol evidence:
{json.dumps(_serialize(matches), indent=2)}
""".strip()

    return client.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
    )