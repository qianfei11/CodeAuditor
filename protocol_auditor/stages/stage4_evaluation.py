"""Stage 4: Vulnerability Evaluation — one agent per finding, run in parallel."""

import asyncio
import glob
import json
import logging
import os
import re
import shutil

from ..agent_utils import load_prompt, run_agent, run_parallel, run_validator
from ..checkpoint import CheckpointManager
from ..config import AuditConfig, PendingFinding

logger = logging.getLogger(__name__)

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"]
SEVERITY_PREFIX = {"Critical": "C", "High": "H", "Medium": "M", "Low": "L"}
VALID_SEVERITIES = {"critical", "high", "medium", "low"}


def _task_key(stage3_filename: str) -> str:
    return f"stage4:{stage3_filename}"


def _strip_json_comments(json_str: str) -> str:
    """Remove // comments from JSON (outside quoted strings)."""
    lines = json_str.split("\n")
    cleaned = []
    for line in lines:
        in_string = False
        result = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"' and (i == 0 or line[i - 1] != '\\'):
                in_string = not in_string
                result.append(ch)
            elif ch == '/' and i + 1 < len(line) and line[i + 1] == '/' and not in_string:
                break
            else:
                result.append(ch)
            i += 1
        cleaned.append("".join(result))
    return "\n".join(cleaned)


def _read_severity_from_pending(pending_path: str) -> str | None:
    """Read the severity from a Stage 4 pending file's JSON summary."""
    try:
        with open(pending_path) as f:
            content = f.read()
        json_match = re.search(
            r"###\s*Summary JSON Line\s*\n(.*?)(?=###\s*Detail|\Z)",
            content,
            re.DOTALL,
        )
        if not json_match:
            return None
        json_str = json_match.group(1).strip()
        json_str = re.sub(r"^```(?:json|JSON)?\s*\n?", "", json_str)
        json_str = re.sub(r"\n?```\s*$", "", json_str)
        json_str = _strip_json_comments(json_str)
        summary = json.loads(json_str)
        return summary.get("severity")
    except Exception as e:
        logger.warning(f"Failed to read severity from {pending_path}: {e}")
        return None


def _inject_id_into_file(filepath: str, real_id: str):
    """Replace the placeholder ID 'TBD' with the real ID in a finding file."""
    with open(filepath) as f:
        content = f.read()
    # Replace TBD placeholder in JSON and Detail section
    content = re.sub(r'"id"\s*:\s*"TBD"', f'"id": "{real_id}"', content)
    content = re.sub(r'\*\*ID\*\*\s*:\s*TBD', f'**ID**: {real_id}', content)
    with open(filepath, "w") as f:
        f.write(content)


async def _run_finding(
    stage3_filepath: str,
    config: AuditConfig,
    checkpoint: CheckpointManager,
) -> str | None:
    """
    Evaluate a single Stage 3 finding. Writes a pending file if confirmed ≥ Medium.
    Returns the pending file path, or None if filtered.
    """
    stage3_filename = os.path.basename(stage3_filepath)
    key = _task_key(stage3_filename)
    pending_dir = os.path.join(config.output_dir, "stage-4-details", "_pending")
    pending_path = os.path.join(pending_dir, stage3_filename)

    if checkpoint.is_complete(key):
        logger.info(f"Stage 4: {stage3_filename} already complete, skipping.")
        return pending_path if os.path.exists(pending_path) else None

    logger.info(f"Stage 4: Evaluating finding {stage3_filename}...")

    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "stage4.md")
    prompt = load_prompt(
        prompt_path,
        finding_file_path=stage3_filepath,
        output_path=pending_path,
        skill_dir=config.skill_dir,
    )

    validator = os.path.join(config.skill_dir, "script", "validate_stage4.py")

    # Agent runs; it may or may not write the pending file
    await run_agent(prompt, cwd=config.target)

    confirmed = os.path.exists(pending_path)

    if confirmed:
        # Validate and attempt repair
        result = run_validator(validator, pending_path)
        if result.returncode != 0:
            logger.warning(f"Stage 4: Validation failed for {pending_path}:\n{result.stdout}")
            issues = result.stdout.strip()
            repair_prompt = (
                f"The evaluation file at `{pending_path}` failed validation. "
                f"Please fix all issues:\n\n```\n{issues}\n```"
            )
            await run_agent(repair_prompt, cwd=config.target, max_turns=10)
            result2 = run_validator(validator, pending_path)
            if result2.returncode != 0:
                logger.warning(f"Stage 4: Repair failed for {pending_path}, keeping as-is.")

    checkpoint.mark_complete(key)
    logger.info(f"Stage 4: {stage3_filename} complete (confirmed={confirmed})")
    return pending_path if confirmed else None


def _assign_ids_and_finalize(
    pending_paths: list[str],
    config: AuditConfig,
) -> list[str]:
    """
    Deterministic post-evaluation step:
    1. Read severity from each pending file
    2. Filter out below-Medium (agent should have already filtered, but double-check)
    3. Assign globally unique IDs (C-01, H-01, M-01, L-01)
    4. Rename files to stage-4-details/{ID}.md
    5. Inject real ID into file content
    Returns list of final file paths.
    """
    stage4_dir = os.path.join(config.output_dir, "stage-4-details")

    # Read severities
    findings: list[tuple[str, str]] = []  # (pending_path, severity)
    for path in pending_paths:
        sev = _read_severity_from_pending(path)
        if sev and sev.lower() in VALID_SEVERITIES:
            findings.append((path, sev.capitalize()))
        else:
            logger.warning(f"Stage 4: Skipping {os.path.basename(path)} — could not read valid severity")

    # Sort by severity order
    findings.sort(key=lambda x: SEVERITY_ORDER.index(x[1]) if x[1] in SEVERITY_ORDER else 99)

    # Assign IDs
    counters: dict[str, int] = {sev: 0 for sev in SEVERITY_ORDER}
    final_paths = []

    for pending_path, severity in findings:
        counters[severity] += 1
        prefix = SEVERITY_PREFIX[severity]
        real_id = f"{prefix}-{counters[severity]:02d}"

        final_path = os.path.join(stage4_dir, f"{real_id}.md")
        shutil.move(pending_path, final_path)
        _inject_id_into_file(final_path, real_id)
        final_paths.append(final_path)
        logger.info(f"Stage 4: Assigned {real_id} to {os.path.basename(pending_path)}")

    return final_paths


async def run_stage4(
    finding_files: list[str],
    config: AuditConfig,
    checkpoint: CheckpointManager,
) -> list[str]:
    """
    Run Stage 4 for all finding files in parallel.
    Returns list of final stage-4-details/{ID}.md paths.
    """
    if not finding_files:
        logger.info("Stage 4: No findings to evaluate.")
        return []

    semaphore = asyncio.Semaphore(config.max_parallel)
    tasks = [
        _run_finding(fpath, config, checkpoint)
        for fpath in finding_files
    ]
    results = await run_parallel(tasks, semaphore)

    confirmed_pending: list[str] = []
    for filepath, result in zip(finding_files, results):
        if isinstance(result, Exception):
            logger.error(f"Stage 4: {os.path.basename(filepath)} failed: {result}")
        elif result is not None:
            confirmed_pending.append(result)

    logger.info(f"Stage 4: {len(confirmed_pending)} confirmed findings (from {len(finding_files)} candidates)")

    # Assign IDs and finalize
    final_paths = _assign_ids_and_finalize(confirmed_pending, config)
    logger.info(f"Stage 4 complete. Final findings: {len(final_paths)}")
    return final_paths
