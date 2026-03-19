from __future__ import annotations

import json
from pathlib import Path

from .schemas import Table2StudyDetails


def save_table2_json(table2: Table2StudyDetails, output_path: Path) -> None:
    output_path.write_text(
        json.dumps(table2.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
