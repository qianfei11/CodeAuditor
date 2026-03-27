from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..agent import run_with_validation
from ..checkpoint import CheckpointManager
from ..config import AuditConfig
from ..logger import get_logger
from ..prompts import load_prompt
from ..validation.stage4 import validate_stage4_file

logger = get_logger("stage4")
_TASK_KEY = "stage4"


@dataclass
class Stage4Output:
    threat_model_path: str
    instruction_stage5_path: str


async def run_stage4(
    config: AuditConfig,
    checkpoint: CheckpointManager,
) -> Stage4Output:
    threat_model_path = os.path.join(config.output_dir, "stage-4-security-context.md")
    instruction_stage5_path = os.path.join(config.output_dir, "stage-4-details", "evaluation-guidance.md")

    if checkpoint.is_complete(_TASK_KEY):
        logger.info("Stage 4 already complete, loading existing output.")
        return Stage4Output(threat_model_path=threat_model_path, instruction_stage5_path=instruction_stage5_path)

    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=int(5 * 365.25))).strftime("%Y-%m-%d")

    prompt = load_prompt("stage4.md", {
        "target_path": config.target,
        "output_path": threat_model_path,
        "instruction_stage5_path": instruction_stage5_path,
        "today": today,
        "start_date": start_date,
        "user_instructions": config.scope or "No additional scope constraints.",
    })

    passed, _ = await run_with_validation(
        prompt=prompt,
        config=config,
        cwd=config.target,
        output_path=threat_model_path,
        validator=validate_stage4_file,
    )

    if not passed:
        logger.warning("Stage 4 validation did not fully pass, continuing with best-effort output.")

    checkpoint.mark_complete(_TASK_KEY)
    logger.info("Stage 4 complete. Threat model: %s", threat_model_path)
    return Stage4Output(threat_model_path=threat_model_path, instruction_stage5_path=instruction_stage5_path)
