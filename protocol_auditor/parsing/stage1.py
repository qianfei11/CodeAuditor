from __future__ import annotations

import json

from ..config import Module


def parse_modules(file_path: str) -> list[Module]:
    with open(file_path) as f:
        data = json.load(f)

    modules: list[Module] = []
    for entry in data.get("modules", []):
        modules.append(Module(
            id=entry["id"],
            name=entry["name"],
            description=entry["description"],
            files_dir=entry.get("files", ""),
            analyze=True,
        ))
    return modules
