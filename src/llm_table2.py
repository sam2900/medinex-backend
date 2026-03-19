from __future__ import annotations
import json
from typing import List, Optional

from .llm_client import AzureOpenAIJsonClient


def _filter_metadata_chunks(matches: List, max_page: int = 5):
    """Keep early pages where protocol metadata usually appears."""
    filtered = [m for m in matches if m.page_num and m.page_num <= max_page]
    return filtered if filtered else matches


def _serialize(matches: List, max_chars=1200):
    out = []
    for m in matches:
        out.append(
            {
                "chunk_id": m.chunk_id,
                "page_num": m.page_num,
                "text": m.text[:max_chars],
            }
        )
    return out


def extract_table2_with_llm(matches: List,
                            client: Optional[AzureOpenAIJsonClient] = None):

    client = client or AzureOpenAIJsonClient()
    matches = _filter_metadata_chunks(matches)

    system_prompt = """
You extract structured metadata from clinical trial protocols.
Return ONLY JSON.
"""

    user_prompt = f"""
Extract the following fields from the protocol:

Protocol date
Protocol number
Indication
Phase
Protocol title

Rules:

Protocol date
- Use the protocol date or document date on the title page.

Protocol number
- Prefer values labeled "Protocol Number".
- If multiple study identifiers appear, prefer the identifier labeled "Protocol Number" or the sponsor protocol identifier.
- Do not leave protocol_number empty if one is present.


Indication
- Return the disease or therapeutic area.
- Prefer concise labels like Oncology, Melanoma, NSCLC, Anesthesiology.

Phase
- Return Roman numeral form: I, II, III, IV.

Protocol title
- Return the full official protocol title.


Return JSON exactly in this format:

{{
  "protocol_date": "",
  "protocol_number": "",
  "indication": "",
  "phase": "",
  "protocol_title": ""
}}

Candidate text:
{json.dumps(_serialize(matches), indent=2)}
"""

    result = client.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0,
    )

    return result