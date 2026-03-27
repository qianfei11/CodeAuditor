from __future__ import annotations

import os

from ..agent import run_with_validation
from ..checkpoint import CheckpointManager
from ..config import AuditConfig, Module
from ..logger import get_logger
from ..parsing.stage1 import parse_modules
from ..prompts import load_prompt
from ..validation.stage1 import validate_stage1_file

logger = get_logger("stage1")
_TASK_KEY = "stage1"


async def run_stage1(config: AuditConfig, checkpoint: CheckpointManager) -> list[Module]:
    output_path = os.path.join(config.output_dir, "stage-1-modules.json")

    if checkpoint.is_complete(_TASK_KEY):
        logger.info("Stage 1 already complete, loading existing output.")
        return parse_modules(output_path)

    prompt = load_prompt("stage1.md", {
        "target_path": config.target,
        "output_path": output_path,
        "user_instructions": config.scope or "No additional scope constraints.",
    })

    passed, _ = await run_with_validation(
        prompt=prompt,
        config=config,
        cwd=config.target,
        output_path=output_path,
        validator=validate_stage1_file,
    )

    if not passed:
        logger.warning("Stage 1 validation did not fully pass, continuing with best-effort output.")

    checkpoint.mark_complete(_TASK_KEY)
    modules = parse_modules(output_path)
    logger.info("Stage 1 complete. Modules: %s", ", ".join(m.id for m in modules))
    return modules
