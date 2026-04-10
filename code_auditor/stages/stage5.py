from __future__ import annotations

import json
import os

from ..agent import run_agent
from ..checkpoint import CheckpointManager
from ..config import AuditConfig
from ..logger import get_logger
from ..prompts import load_prompt
from ..utils import run_parallel_limited

logger = get_logger("stage5")

# Stage 5 agents need generous turn budgets — PoC development involves
# building projects, writing exploit code, running/debugging, and iterating.
_MAX_TURNS = 500


def _task_key(vuln_id: str) -> str:
    return f"stage5:{vuln_id}"


def _read_vuln_id(file_path: str) -> str | None:
    try:
        with open(file_path) as f:
            data = json.load(f)
        return data.get("id")
    except Exception as e:
        logger.warning("Failed to read vuln id from %s: %s", file_path, e)
        return None


async def _run_reproduce(
    vuln_file_path: str,
    config: AuditConfig,
    checkpoint: CheckpointManager,
) -> str | None:
    """Reproduce a single verified vulnerability and develop a PoC."""
    vuln_id = _read_vuln_id(vuln_file_path)
    if not vuln_id:
        logger.warning("Stage 5: Cannot read vulnerability ID from %s, skipping.", vuln_file_path)
        return None

    key = _task_key(vuln_id)
    poc_dir = os.path.join(config.output_dir, "stage-5-details", vuln_id)
    report_path = os.path.join(poc_dir, "report.md")

    if checkpoint.is_complete(key):
        logger.info("Stage 5: %s already complete, skipping.", vuln_id)
        return report_path if os.path.exists(report_path) else None

    logger.info("Stage 5: Starting PoC reproduction for %s.", vuln_id)
    os.makedirs(poc_dir, exist_ok=True)

    prompt = load_prompt("stage5.md", {
        "finding_file_path": vuln_file_path,
        "target_path": config.target,
        "poc_dir": poc_dir,
        "finding_id": vuln_id,
    })

    await run_agent(
        prompt,
        config,
        cwd=config.target,
        max_turns=_MAX_TURNS,
    )

    checkpoint.mark_complete(key)

    has_report = os.path.exists(report_path)
    logger.info("Stage 5: %s complete (report=%s)", vuln_id, has_report)
    return report_path if has_report else None


async def run_stage5(
    vuln_files: list[str],
    config: AuditConfig,
    checkpoint: CheckpointManager,
) -> list[str]:
    """Run PoC reproduction for each verified vulnerability in parallel."""
    if not vuln_files:
        logger.info("Stage 5: No verified vulnerabilities to reproduce.")
        return []

    logger.info("Stage 5: Reproducing %d verified vulnerabilities.", len(vuln_files))

    results = await run_parallel_limited(
        vuln_files,
        config.max_parallel,
        lambda vf, _: _run_reproduce(vf, config, checkpoint),
    )

    reports: list[str] = []
    for i, (status, value, error) in enumerate(results):
        if i >= len(vuln_files):
            continue
        if status == "rejected":
            logger.error("Stage 5: %s failed: %s", os.path.basename(vuln_files[i]), error)
            continue
        if value:
            reports.append(value)

    logger.info("Stage 5 complete. %d reports generated (from %d vulnerabilities).", len(reports), len(vuln_files))
    return reports
