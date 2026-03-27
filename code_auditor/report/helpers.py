from __future__ import annotations

from pathlib import Path


def list_markdown_files_sync(dir_path: str) -> list[str]:
    p = Path(dir_path)
    if not p.is_dir():
        return []
    return sorted(str(f) for f in p.iterdir() if f.is_file() and f.suffix == ".md")


def list_json_files_sync(dir_path: str) -> list[str]:
    p = Path(dir_path)
    if not p.is_dir():
        return []
    return sorted(str(f) for f in p.iterdir() if f.is_file() and f.suffix == ".json")
