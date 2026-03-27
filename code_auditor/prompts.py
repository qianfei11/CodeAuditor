from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(prompt_name: str, substitutions: dict[str, str]) -> str:
    text = (PROMPTS_DIR / prompt_name).read_text()
    for key, value in substitutions.items():
        text = text.replace(f"__{key.upper()}__", value)
    return text
