from __future__ import annotations

import os
import re

from ..agent import run_agent
from ..checkpoint import CheckpointManager
from ..config import AnalysisUnit, AuditConfig
from ..logger import get_logger
from ..prompts import load_prompt
from ..utils import format_validation_issues, list_matching_files, run_parallel_limited
from ..validation.stage4 import validate_stage4_file

logger = get_logger("stage4")


def _task_key(unit: AnalysisUnit) -> str:
    return f"stage4:{unit.id}"


async def _run_unit(
    unit: AnalysisUnit,
    config: AuditConfig,
    checkpoint: CheckpointManager,
    auditing_focus_path: str,
    vuln_criteria_path: str,
) -> list[str]:
    key = _task_key(unit)
    result_dir = os.path.join(config.output_dir, "stage-4-details")
    escaped_id = re.escape(unit.id)
    finding_pattern = re.compile(rf"^{escaped_id}-F-\d+\.json$")

    if checkpoint.is_complete(key):
        logger.info("Stage 4: %s already complete, skipping.", unit.id)
        return list_matching_files(result_dir, finding_pattern)

    logger.info("Stage 4: Starting bug discovery for %s.", unit.id)
    prompt = load_prompt("stage4.md", {
        "au_file_path": unit.au_file_path,
        "result_dir": result_dir,
        "finding_prefix": unit.id,
        "auditing_focus_path": auditing_focus_path,
        "vuln_criteria_path": vuln_criteria_path,
    })

    await run_agent(prompt, config, cwd=config.target)

    finding_files = list_matching_files(result_dir, finding_pattern)
    for finding_file in finding_files:
        issues = validate_stage4_file(finding_file)
        if not issues:
            continue

        logger.warning("Stage 4: Validation failed for %s\n%s", finding_file, format_validation_issues(issues))
        repair_prompt = (
            f"The finding file at `{finding_file}` failed validation. "
            f"Please fix all issues listed below:\n\n```\n{format_validation_issues(issues)}\n```"
        )
        await run_agent(repair_prompt, config, cwd=config.target, max_turns=10)

        issues = validate_stage4_file(finding_file)
        if issues:
            logger.warning("Stage 4: Repair failed for %s\n%s", finding_file, format_validation_issues(issues))

    checkpoint.mark_complete(key)
    logger.info("Stage 4: %s complete. Findings: %s", unit.id, len(finding_files))
    return finding_files


async def run_stage4(
    units: list[AnalysisUnit],
    config: AuditConfig,
    checkpoint: CheckpointManager,
    auditing_focus_path: str,
    vuln_criteria_path: str,
) -> list[str]:
    if not units:
        logger.warning("Stage 4: No analysis units to process.")
        return []

    results = await run_parallel_limited(
        units,
        config.max_parallel,
        lambda unit, _: _run_unit(unit, config, checkpoint, auditing_focus_path, vuln_criteria_path),
    )

    all_finding_files: list[str] = []
    for i, (status, value, error) in enumerate(results):
        if i >= len(units):
            continue
        if status == "rejected":
            logger.error("Stage 4: %s failed: %s", units[i].id, error)
            continue
        if value:
            all_finding_files.extend(value)

    logger.info("Stage 4 complete. Total bug finding files: %s", len(all_finding_files))
    return all_finding_files
