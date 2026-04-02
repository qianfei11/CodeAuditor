from __future__ import annotations

import json

from ..config import ValidationIssue
from .common import read_file_or_issues

_PLACEHOLDERS = {"none", "n/a", "...", "tbd", ""}


def _is_blank(value: object) -> bool:
    if isinstance(value, str):
        return value.lower().strip() in _PLACEHOLDERS
    if isinstance(value, list):
        return len(value) == 0
    return not value


def validate_stage3_file(file_path: str) -> list[ValidationIssue]:
    content, issues = read_file_or_issues(file_path)
    if issues:
        return issues

    if not content.strip():
        return [ValidationIssue(
            description="Analysis unit file is empty.",
            expected="A JSON object with description, files, and focus fields.",
            fix="Write the analysis unit definition as JSON to this file.",
        )]

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return [ValidationIssue(
            description=f"Invalid JSON: {e}",
            expected="Valid JSON.",
            fix="Fix the JSON syntax error.",
        )]

    validation_issues: list[ValidationIssue] = []

    if _is_blank(data.get("description")):
        validation_issues.append(ValidationIssue(
            description='Missing or blank "description".',
            expected="A short description of what this unit covers.",
            fix='Add a "description" field.',
        ))
    if _is_blank(data.get("files")):
        validation_issues.append(ValidationIssue(
            description='Missing or empty "files".',
            expected="A non-empty array of source file paths.",
            fix='Add a "files" array with at least one path.',
        ))
    if _is_blank(data.get("focus")):
        validation_issues.append(ValidationIssue(
            description='Missing or blank "focus".',
            expected="Concrete analysis guidance.",
            fix='Add a "focus" field with actionable analysis guidance.',
        ))

    return validation_issues
