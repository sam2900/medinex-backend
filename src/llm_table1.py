from __future__ import annotations

import json
from typing import List, Optional

from .llm_client import AzureOpenAIJsonClient


def _serialize(matches: List, max_chars: int = 1600) -> list[dict]:
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


def extract_table1_with_llm(
    matches: List,
    client: Optional[AzureOpenAIJsonClient] = None,
) -> dict:
    client = client or AzureOpenAIJsonClient()

    system_prompt = """
You extract the country for a clinical trial budget estimation table.
Return ONLY valid JSON.
Use only the provided protocol evidence.
""".strip()

    user_prompt = f"""
Extract the study country from this protocol.

Rules:
1. Return the country most relevant to the protocol budgeting context.
2. If a country is explicitly shown in a summary table, title page, registry content, or country-specific section, prefer that.
3. If the protocol is global/multi-country and no single country can be determined, return "Global".
4. Do not guess beyond the evidence.

Return JSON exactly like this:
{{
  "country": "string"
}}

Protocol evidence:
{json.dumps(_serialize(matches), indent=2)}
""".strip()

    return client.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
    )