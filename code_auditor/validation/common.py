from __future__ import annotations

import re

from ..config import ValidationIssue


def file_missing_issue(file_path: str) -> ValidationIssue:
    return ValidationIssue(
        description=f'Output file not found: "{file_path}"',
        expected="The file should exist at the specified path.",
        fix="Ensure the output file was written to the correct path.",
    )


def read_file_or_issues(file_path: str) -> tuple[str, list[ValidationIssue]]:
    try:
        with open(file_path) as f:
            return f.read(), []
    except FileNotFoundError:
        return "", [file_missing_issue(file_path)]


def find_section(content: str, heading: str) -> str | None:
    escaped = re.escape(heading)
    pattern = re.compile(rf"(?:^|\n)##\s+{escaped}\s*\n([\s\S]*?)(?=\n## |$)")
    m = pattern.search(content)
    if m is None:
        return None
    return m.group(1).strip() or None


def parse_markdown_table_rows(section_text: str) -> list[list[str]]:
    table_lines = [line for line in section_text.split("\n") if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return []
    # Skip header and separator rows
    return [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in table_lines[2:]
    ]


def check_field(block_text: str, field_name: str) -> str | None:
    escaped = re.escape(field_name)
    pattern = re.compile(rf"\*\*{escaped}\*\*\s*:\s*(.+)")
    m = pattern.search(block_text)
    if m is None:
        return None
    return m.group(1).strip()


def strip_json_comments(json_text: str) -> str:
    lines: list[str] = []
    for line in json_text.split("\n"):
        in_string = False
        result: list[str] = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"' and (i == 0 or line[i - 1] != "\\"):
                in_string = not in_string
                result.append(ch)
            elif not in_string and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break
            else:
                result.append(ch)
            i += 1
        lines.append("".join(result))
    return "\n".join(lines)


def strip_code_fence(text: str) -> str:
    text = re.sub(r"^```(?:json|JSON)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()
