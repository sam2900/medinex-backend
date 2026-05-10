from __future__ import annotations

import json
from typing import List, Optional

from .llm_client import AzureOpenAIJsonClient


def _filter_soa_chunks(matches: List, max_page: int = 140) -> List:
    filtered = [
        m for m in matches
        if getattr(m, "page_num", None) is not None and m.page_num <= max_page
    ]
    return filtered if filtered else matches


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


def extract_table4_with_llm(
    matches: List,
    visit_columns: List[str],
    client: Optional[AzureOpenAIJsonClient] = None,
) -> dict:
    client = client or AzureOpenAIJsonClient()
    matches = _filter_soa_chunks(matches)

    system_prompt = """
You extract a normalized operational procedure list for a clinical trial budget template.
Return ONLY valid JSON.
Use only the provided candidate text.
""".strip()

    user_prompt = f"""
Extract Table #4: List of Procedures.

Goal:
- Build a normalized procedure list from the Schedule of Activities and related procedure text.
- This is a curated operational procedure list, not a literal copy of every raw row.
- Include procedures that are operationally relevant for the budget template.

Important output rules:
1. Keep "code" blank for every row.
2. Keep "budget" blank for every row.
3. For each procedure row, mark the visit columns where that procedure occurs.
   - Use "X" when the procedure is performed at that visit.
   - Use "" when it is not performed at that visit.
4. Decide "unit_basis" as either:
   - "Per Assessment"
   - "Per Procedure"
5. Do not invent procedures unsupported by the evidence.
6. Do not output duplicate procedures.
7. Preserve a sensible study workflow order.
8. Do NOT include footer rows like blank rows or Procedures Sub-Total. Python will add those later.
9. Return visit_values keys for all visit columns provided below.
10. Do not mark a visit unless the evidence supports that the procedure occurs there.

Strong normalization guidance:
- Prefer these canonical procedure names when supported:
  - Informed Consent
  - Participant Identification Card
  - Screening Number Assignment
  - Medical History
  - Inclusion/Exclusion Criteria
  - Prior/Concomitant Medication Review
  - Treatment Asssignment or Randomization
  - Administration of NMBA
  - Administration of Study Treatment
  - Extubation Readiness Assessment
  - Neuromuscular Monitoring
  - Full Physical Examination
  - Targeted Physical Examination
  - Physical Examination
  - Vital Signs
  - Height/weight/BMI workflow
  - Continuous Heart Rate Monitoring (ECG)
  - Electrocardiogram
  - Hematology
  - Chemistry
  - Coagulation
  - Urinalysis, dipstick
  - Additional Mandatory laboratory
  - ECG
  - MRI or CT Brain
  - Plasma PK Sample (2 mL)
  - Plasma Biomarkers (10 mL)
  - Tumor Tissue Sample
  - AE/SAE/ECI review
  - Adverse Device Event Monitoring
  - Demographics
  - ECOG Performance Status
  - EQ-5D administration
  - INT-QLQC-64

Specific guidance:
- Do not merge "Vital Signs" with "Height/weight/BMI workflow".
- Prefer separate rows when the evidence supports separate procedures.
- If the protocol has broad laboratory wording, prefer specific operational rows when clearly supported.
- Exclude obvious non-procedure notes, footnotes, and narrative explanations.

Visit columns for this protocol:
{json.dumps(visit_columns)}

Return JSON exactly in this format:
{{
  "procedures": [
    {{
      "procedure": "string",
      "code": "",
      "unit_basis": "Per Assessment or Per Procedure or blank",
      "budget": "",
      "visit_values": {{
        "SCR": "",
        "V2": "",
        "V3": "",
        "FU14": "",
        "USV": ""
      }}
    }}
  ]
}}

Candidate text:
{json.dumps(_serialize(matches), indent=2)}
""".strip()

    return client.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
    )
