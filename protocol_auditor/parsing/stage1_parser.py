"""Parse stage-1-scope.md to extract the list of modules."""

import re

from ..config import Module


def parse_modules(filepath: str) -> list[Module]:
    """Parse stage-1-scope.md and return all modules."""
    with open(filepath) as f:
        content = f.read()
    return _extract_modules(content)


def get_in_scope_modules(filepath: str) -> list[Module]:
    """Return only modules marked for analysis (verdict contains 'yes')."""
    return [m for m in parse_modules(filepath) if m.analyze]


def _extract_modules(content: str) -> list[Module]:
    # Find Module Structure section
    section_match = re.search(
        r"##\s+Module Structure\s*\n(.*?)(?=\n## |\Z)",
        content,
        re.DOTALL,
    )
    if not section_match:
        return []

    section = section_match.group(1)
    modules = []

    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 5:
            continue

        module_id = cells[0].strip()
        if not re.match(r"^M-\d+$", module_id):
            continue  # Skip header / separator rows

        name = cells[1].strip()
        description = cells[2].strip()
        files_dir = cells[3].strip()
        verdict = cells[4].strip()
        analyze = "yes" in verdict.lower()

        modules.append(Module(
            id=module_id,
            name=name,
            description=description,
            files_dir=files_dir,
            analyze=analyze,
        ))

    return modules
