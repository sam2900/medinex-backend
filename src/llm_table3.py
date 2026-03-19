from __future__ import annotations

import json
from typing import List, Optional

from .llm_client import AzureOpenAIJsonClient


def _filter_visit_chunks(matches: List, max_page: int = 140) -> List:
    """
    SoA / visit schedules / appendix pages are often later in the protocol.
    Keep a broad range for now.
    """
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


def extract_table3_soa_evidence(
    matches: List,
    client: Optional[AzureOpenAIJsonClient] = None,
) -> dict:
    """
    Stage 1:
    Extract raw SoA / footnote evidence without forcing final visit construction yet.
    """
    client = client or AzureOpenAIJsonClient()
    matches = _filter_visit_chunks(matches)

    system_prompt = """
You extract structured visit-schedule evidence from a clinical trial protocol.
Return ONLY valid JSON.
Use only the provided candidate text.
""".strip()

    user_prompt = f"""
Extract structured evidence for visit construction from the protocol.

Goal:
- Read Schedule of Activities / visit schedule / footnotes / notes.
- Capture raw evidence needed to construct the budgeting visit table later.
- Do NOT over-normalize into the final visit list yet.
- Focus on:
  - named visits
  - cadence labels
  - explicit weeks/days
  - recurring visit rules
  - conditional imaging/tumor-assessment rules
  - footnotes that modify generic cadence

Return JSON exactly like this:
{{
  "explicit_named_visits": [
    {{
      "label": "Screening",
      "timing": "Days -28 to -1",
      "raw_text": "..."
    }}
  ],
  "cadence_rules": [
    {{
      "label": "Q2W",
      "raw_text": "...",
      "start_after": "",
      "end_after": "",
      "weeks_explicitly_supported": ["2", "6", "10", "12"]
    }}
  ],
  "conditional_assessment_rules": [
    {{
      "assessment": "Tumor Assessment",
      "rule": "conditional / clinically indicated / progression-driven / every 8 weeks / etc.",
      "raw_text": "..."
    }}
  ],
  "footnotes": [
    {{
      "footnote_id": "h",
      "meaning": "summary of footnote effect",
      "raw_text": "..."
    }}
  ],
  "terminal_visits": [
    {{
      "label": "Treatment Discontinuation",
      "timing": "28 days after final dose",
      "raw_text": "..."
    }},
    {{
      "label": "Long term follow up",
      "timing": "",
      "raw_text": "..."
    }}
  ],
  "notes_for_budget_logic": [
    "string"
  ]
}}

Important extraction rules:
1. Capture explicit evidence, not guesses.
2. If footnotes restrict a generic cadence to only specific weeks, capture those specific weeks.
3. If imaging / disease assessment appears conditional, progression-driven, or clinically indicated, capture that as a conditional rule.
4. If a recurring cadence exists after a certain point (e.g. every 4 weeks after Week 12), capture it.
5. Preserve evidence text in concise form.

Candidate text:
{json.dumps(_serialize(matches), indent=2)}
""".strip()

    return client.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
    )


def construct_table3_budget_visits(
    soa_evidence: dict,
    client: Optional[AzureOpenAIJsonClient] = None,
) -> dict:
    """
    Stage 2:
    Convert raw evidence into final budgeting visits.
    """
    client = client or AzureOpenAIJsonClient()

    system_prompt = """
You construct a normalized budgeting visit list for a clinical trial.
Return ONLY valid JSON.
Use only the provided structured evidence.
""".strip()

    user_prompt = f"""
Construct the final normalized budgeting visit table from the structured SoA evidence.

Goal:
- Output only the visits that should exist in the budgeting structure.
- Use footnotes AND procedure timing logic to determine valid visits.
- Do NOT expand cadence blindly.

CRITICAL VISIT CREATION RULES:
1. A visit should ONLY be created if:
   - There is clear procedural activity at that timepoint
   - OR the visit is a required structural visit (SCR, BW1, TD, OFFTX, LTFU, USV)

2. DO NOT expand cadence mechanically:
   - Q2W does NOT mean all weeks (2,4,6,8,10,12)
   - Q4W does NOT mean (16,20,24,...)

3. Use footnotes and evidence to restrict cadence:
   - If additional assessments occur only at specific weeks → only those weeks become visits
   - If no procedures occur at a cadence timepoint → DO NOT create that visit

4. Conditional / imaging logic:
   - Tumor assessments (Q8W) → DO NOT create visits
   - Imaging (CT/MRI) → DO NOT create visits
   - PK / biomarker sampling → DO NOT create visits
   → These go to Conditional Procedures, not visits

5. Recurring visits:
   - After Week 12, represent Q4W as a SINGLE normalized visit:
     "Q4W (until PD)"
   - DO NOT expand into Q4W16, Q4W20, etc.

6. Ordering:
   SCR → BW1 → Q2W visits → Q4W → TD → OFFTX → LTFU → USV

7. Always include:
   - Unscheduled Visit (USV)

8. For explicit-visit studies, prefer the named visits from the source table:
   - Screening
   - Peri-anesthetic
   - Post-anesthetic
   - Follow-up
   rather than inventing cadence-style visits.

Return JSON exactly like:
{{
  "visits": [
    {{
      "visit_title": "Q2W (Week 2)",
      "visit_id": "Q2W2",
      "why_included": "..."
    }}
  ],
  "excluded_candidate_visits": [
    {{
      "candidate": "Q2W (Week 4)",
      "reason": "no procedural activity at this timepoint"
    }}
  ]
}}

Structured evidence:
{json.dumps(soa_evidence, indent=2)}
"""

    return client.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
    )