from __future__ import annotations

from ..config import ValidationIssue
from .common import find_section, read_file_or_issues


def validate_stage4_file(file_path: str) -> list[ValidationIssue]:
    content, issues = read_file_or_issues(file_path)
    if issues:
        return issues

    if not content.strip():
        return [ValidationIssue(
            description="Output file is empty.",
            expected='A security context report with "## Project Summary" and "## Attacker Profile" sections.',
            fix="Write the full Stage 4 security context report to this file.",
        )]

    validation_issues: list[ValidationIssue] = []
    for section_name in ("Project Summary", "Attacker Profile"):
        section = find_section(content, section_name)
        if section is None:
            validation_issues.append(ValidationIssue(
                description=f'Missing required section: "## {section_name}"',
                expected=f'A "## {section_name}" heading must be present.',
                fix=f'Add a "## {section_name}" section with appropriate content.',
            ))

    return validation_issues
