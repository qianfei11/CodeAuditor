"""Stage 2: Identify Entry Points — one agent per module, run in parallel."""

import asyncio
import logging
import os

from ..agent_utils import load_prompt, run_parallel, run_with_validation
from ..checkpoint import CheckpointManager
from ..config import AuditConfig, EntryPoint, Module
from ..parsing.stage2_parser import parse_entry_points

logger = logging.getLogger(__name__)


def _task_key(module: Module) -> str:
    return f"stage2:{module.id}"


async def _run_module(
    module: Module,
    config: AuditConfig,
    checkpoint: CheckpointManager,
    stage1_output: str,
) -> list[EntryPoint]:
    key = _task_key(module)
    result_dir = os.path.join(config.output_dir, "stage-2-details")
    output_path = os.path.join(result_dir, f"{module.id}.md")

    if checkpoint.is_complete(key):
        logger.info(f"Stage 2: {module.id} already complete, loading existing output.")
        return parse_entry_points(output_path, module.id)

    logger.info(f"Stage 2: Running entry point analysis for {module.id} ({module.name})...")

    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "stage2.md")
    prompt = load_prompt(
        prompt_path,
        stage1_output_path=stage1_output,
        result_dir=result_dir,
        module_id=module.id,
        skill_dir=config.skill_dir,
    )

    validator = os.path.join(config.skill_dir, "script", "validate_stage2.py")
    passed, _ = await run_with_validation(
        prompt=prompt,
        cwd=config.target,
        output_path=output_path,
        validator_script=validator,
    )

    if not passed:
        logger.warning(f"Stage 2: {module.id} validation did not fully pass.")

    checkpoint.mark_complete(key)
    eps = parse_entry_points(output_path, module.id)
    logger.info(f"Stage 2: {module.id} complete. Entry points: {[ep.id for ep in eps]}")
    return eps


async def run_stage2(
    modules: list[Module],
    config: AuditConfig,
    checkpoint: CheckpointManager,
) -> dict[str, list[EntryPoint]]:
    """
    Run Stage 2 for all modules in parallel.
    Returns mapping from module_id → list of EntryPoint.
    """
    stage1_output = os.path.join(config.output_dir, "stage-1-scope.md")
    semaphore = asyncio.Semaphore(config.max_parallel)

    tasks = [
        _run_module(module, config, checkpoint, stage1_output)
        for module in modules
    ]
    results = await run_parallel(tasks, semaphore)

    ep_map: dict[str, list[EntryPoint]] = {}
    for module, result in zip(modules, results):
        if isinstance(result, Exception):
            logger.error(f"Stage 2: {module.id} failed with exception: {result}")
            ep_map[module.id] = []
        else:
            ep_map[module.id] = result

    return ep_map
