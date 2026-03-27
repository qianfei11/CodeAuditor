from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class DraftUnit:
    description: str
    files: list[str]
    focus: str


def parse_au_file(file_path: str) -> DraftUnit:
    """Parse a single analysis unit JSON file."""
    with open(file_path) as f:
        data = json.load(f)
    return DraftUnit(
        description=data.get("description", ""),
        files=data.get("files", []),
        focus=data.get("focus", ""),
    )
