from __future__ import annotations

import json
import re

from ..config import ValidationIssue
from .common import read_file_or_issues


def validate_stage2_file(file_path: str) -> list[ValidationIssue]:
    content, issues = read_file_or_issues(file_path)
    if issues:
        return issues

    if not content.strip():
        return [ValidationIssue(
            description="Output file is empty.",
            expected='A JSON file with "project_summary" and "modules" fields.',
            fix="Write the stage 2 module structure output as JSON to this file.",
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

    if "project_summary" not in data:
        validation_issues.append(ValidationIssue(
            description='Missing required key: "project_summary".',
            expected='A "project_summary" object with project metadata.',
            fix='Add a "project_summary" object with "path", "name", "language", "description" fields.',
        ))

    if "modules" not in data:
        validation_issues.append(ValidationIssue(
            description='Missing required key: "modules".',
            expected='A "modules" array with at least one module.',
            fix='Add a "modules" array with module objects.',
        ))
    elif not isinstance(data["modules"], list) or len(data["modules"]) == 0:
        validation_issues.append(ValidationIssue(
            description="Modules array is empty or not an array.",
            expected="At least one module in the modules array.",
            fix='Add module objects to the "modules" array.',
        ))
    else:
        for i, module in enumerate(data["modules"]):
            module_id = module.get("id", "")
            if not re.match(r"^M-\d+$", module_id):
                validation_issues.append(ValidationIssue(
                    description=f'Module {i + 1}: id "{module_id}" does not match expected format.',
                    expected='Module IDs must match "M-{N}" (e.g., "M-1").',
                    fix=f'Change id to "M-{i + 1}".',
                ))
            for key in ("name", "description", "files"):
                if key not in module or not module[key]:
                    validation_issues.append(ValidationIssue(
                        description=f'Module {module_id or i + 1}: missing or empty "{key}".',
                        expected=f'Each module must have a non-empty "{key}" field.',
                        fix=f'Add "{key}" to module {module_id or i + 1}.',
                    ))

    return validation_issues
