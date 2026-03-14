"""Stage 1: Orient and Scope — single agent, produces stage-1-scope.md."""

import logging
import os

from ..agent_utils import load_prompt, run_with_validation
from ..checkpoint import CheckpointManager
from ..config import AuditConfig
from ..parsing.stage1_parser import get_in_scope_modules
from ..config import Module

logger = logging.getLogger(__name__)

TASK_KEY = "stage1"


async def run_stage1(config: AuditConfig, checkpoint: CheckpointManager) -> list[Module]:
    """
    Run Stage 1. Returns list of in-scope modules.
    Skips agent execution if already checkpointed.
    """
    output_path = os.path.join(config.output_dir, "stage-1-scope.md")

    if checkpoint.is_complete(TASK_KEY):
        logger.info("Stage 1 already complete, loading existing output.")
        return get_in_scope_modules(output_path)

    logger.info("Stage 1: Running scope analysis agent...")

    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "stage1.md")
    prompt = load_prompt(
        prompt_path,
        target_path=config.target,
        output_path=output_path,
        skill_dir=config.skill_dir,
        threat_model=config.threat_model,
        user_instructions=config.scope or "No additional scope constraints.",
    )

    validator = os.path.join(config.skill_dir, "script", "validate_stage1.py")
    passed, _ = await run_with_validation(
        prompt=prompt,
        cwd=config.target,
        output_path=output_path,
        validator_script=validator,
    )

    if not passed:
        logger.warning("Stage 1 validation did not fully pass, continuing with best-effort output.")

    checkpoint.mark_complete(TASK_KEY)
    modules = get_in_scope_modules(output_path)
    logger.info(f"Stage 1 complete. In-scope modules: {[m.id for m in modules]}")
    return modules
