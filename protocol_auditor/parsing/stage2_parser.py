"""Parse M-{ID}.md to extract entry points."""

import re

from ..config import EntryPoint


def parse_entry_points(filepath: str, module_id: str) -> list[EntryPoint]:
    """Parse a Stage 2 output file and return all entry points."""
    with open(filepath) as f:
        content = f.read()
    return _extract_entry_points(content, module_id)


def _get_field(block: str, field_name: str) -> str:
    """Extract a bold field value from a markdown block."""
    pattern = r"\*\*" + re.escape(field_name) + r"\*\*\s*:\s*(.+)"
    m = re.search(pattern, block)
    return m.group(1).strip() if m else ""


def _extract_entry_points(content: str, module_id: str) -> list[EntryPoint]:
    pattern = r"###\s+EP-(\d+)\s*:"
    splits = re.split(pattern, content)
    # splits: [preamble, num1, block1, num2, block2, ...]

    entry_points = []
    for i in range(1, len(splits) - 1, 2):
        ep_num = splits[i]
        ep_id = f"EP-{ep_num}"
        block = splits[i + 1]

        ep_type_raw = _get_field(block, "Type")
        # Normalize: "P (Parser)" → "P", "H" → "H", etc.
        type_letter = ep_type_raw.split()[0].strip("()").upper() if ep_type_raw else "P"

        raw_block = f"### {ep_id}:\n{block}"

        entry_points.append(EntryPoint(
            id=ep_id,
            module_id=module_id,
            type=type_letter,
            module_name=_get_field(block, "Module Name"),
            location=_get_field(block, "Location"),
            attacker_controlled_data=_get_field(block, "Attacker-controlled data"),
            initial_validation=_get_field(block, "Initial validation observed"),
            analysis_hints=_get_field(block, "Analysis hints"),
            raw_block=raw_block,
        ))

    return entry_points
