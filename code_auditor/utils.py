from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Callable, Coroutine, TypeVar

from .config import ValidationIssue

T = TypeVar("T")
R = TypeVar("R")


async def run_parallel_limited(
    items: list[T],
    concurrency: int,
    worker: Callable[[T, int], Coroutine[Any, Any, R]],
) -> list[tuple[str, R | None, Exception | None]]:
    """Run worker on each item with bounded concurrency. Returns (status, value, error) triples."""
    if not items:
        return []

    sem = asyncio.Semaphore(max(1, concurrency))
    results: list[tuple[str, R | None, Exception | None]] = [("pending", None, None)] * len(items)

    async def run_one(index: int, item: T) -> None:
        async with sem:
            try:
                value = await worker(item, index)
                results[index] = ("fulfilled", value, None)
            except Exception as exc:
                results[index] = ("rejected", None, exc)

    await asyncio.gather(*(run_one(i, item) for i, item in enumerate(items)))
    return results


def _natural_sort_key(s: str) -> list:
    """Sort key for natural ordering of strings containing numbers.

    Ensures e.g. 'AU-2' sorts before 'AU-10' instead of after 'AU-1'.
    """
    return [int(c) if c.isdigit() else c for c in re.split(r"(\d+)", s)]


def list_markdown_files(dir_path: str) -> list[str]:
    p = Path(dir_path)
    if not p.is_dir():
        return []
    return sorted((str(f) for f in p.iterdir() if f.is_file() and f.suffix == ".md"), key=_natural_sort_key)


def list_json_files(dir_path: str) -> list[str]:
    p = Path(dir_path)
    if not p.is_dir():
        return []
    return sorted((str(f) for f in p.iterdir() if f.is_file() and f.suffix == ".json"), key=_natural_sort_key)


def list_matching_files(dir_path: str, pattern: re.Pattern[str]) -> list[str]:
    p = Path(dir_path)
    if not p.is_dir():
        return []
    return sorted((str(f) for f in p.iterdir() if f.is_file() and pattern.search(f.name)), key=_natural_sort_key)


def compare_severity_then_id(a: str, b: str) -> int:
    """Compare two finding file paths by severity prefix then name."""
    rank = {"C": 0, "H": 1, "M": 2, "L": 3}

    def severity_rank(filepath: str) -> int:
        stem = Path(filepath).stem
        prefix = stem.split("-", 1)[0]
        return rank.get(prefix, 99)

    r = severity_rank(a) - severity_rank(b)
    if r != 0:
        return r
    return (a > b) - (a < b)


def format_validation_issues(issues: list[ValidationIssue]) -> str:
    if not issues:
        return "PASS: All checks passed."
    lines = [f"FAIL: {len(issues)} issue(s) found", ""]
    for i, issue in enumerate(issues, 1):
        lines.append(f"[Issue {i}] {issue.description}")
        lines.append(f"  Expected: {issue.expected}")
        lines.append(f"  Fix: {issue.fix}")
        lines.append("")
    return "\n".join(lines).rstrip()
