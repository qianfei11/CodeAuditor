from __future__ import annotations

import json

from ..config import ValidationIssue
from .common import read_file_or_issues

_REQUIRED_KEYS = ["id", "title", "location", "cwe_id", "vulnerability_class", "cvss_score", "severity"]
_VALID_SEVERITIES = {"critical", "high", "medium", "low"}


def validate_stage5_file(file_path: str) -> list[ValidationIssue]:
    content, issues = read_file_or_issues(file_path)
    if issues:
        return issues

    if not content.strip():
        return [ValidationIssue(
            description="Output file is empty.",
            expected="A JSON object with evaluated finding details.",
            fix="Write the evaluated finding as a JSON object.",
        )]

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return [ValidationIssue(
            description=f"Invalid JSON: {e}",
            expected="Valid JSON.",
            fix="Fix the JSON syntax error (trailing commas, missing quotes, etc.).",
        )]

    validation_issues: list[ValidationIssue] = []

    for key in _REQUIRED_KEYS:
        if key not in data:
            validation_issues.append(ValidationIssue(
                description=f'Missing required key: "{key}".',
                expected=f'The JSON object must contain "{key}".',
                fix=f'Add "{key}" to the JSON object.',
            ))

    severity = data.get("severity", "")
    if isinstance(severity, str) and severity and severity.lower() not in _VALID_SEVERITIES:
        validation_issues.append(ValidationIssue(
            description=f'Invalid severity: "{severity}".',
            expected="One of: Critical, High, Medium, Low.",
            fix='Change "severity" to one of: "Critical", "High", "Medium", "Low".',
        ))

    return validation_issues
