"""Stage 3: Vulnerability Analysis — one agent per entry point, run in parallel."""

import asyncio
import glob
import logging
import os

from ..agent_utils import load_prompt, run_parallel, run_with_validation, run_validator
from ..checkpoint import CheckpointManager
from ..config import AuditConfig, EntryPoint

logger = logging.getLogger(__name__)

VALID_SEVERITIES = {"Critical", "High", "Medium", "Low"}


def _task_key(ep: EntryPoint) -> str:
    return f"stage3:{ep.module_id}:{ep.id}"


def _detect_checklist(config: AuditConfig) -> str:
    """Detect project language from file extensions and return checklist path."""
    ext_counts = {"c_cpp": 0, "go": 0, "rust": 0, "managed": 0}
    for root, _, files in os.walk(config.target):
        # Skip hidden dirs and common non-source dirs
        if any(part.startswith(".") or part in ("vendor", "node_modules", "target", "__pycache__")
               for part in root.split(os.sep)):
            continue
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp"):
                ext_counts["c_cpp"] += 1
            elif ext == ".go":
                ext_counts["go"] += 1
            elif ext == ".rs":
                ext_counts["rust"] += 1
            elif ext in (".py", ".java", ".cs", ".rb", ".php"):
                ext_counts["managed"] += 1

    dominant = max(ext_counts, key=lambda k: ext_counts[k])
    checklist_map = {
        "c_cpp": "checklist-c-cpp.md",
        "go": "checklist-go.md",
        "rust": "checklist-rust.md",
        "managed": "checklist-managed.md",
    }
    checklist_file = checklist_map.get(dominant, "checklist-c-cpp.md")
    checklist_path = os.path.join(config.skill_dir, "reference", checklist_file)

    if os.path.exists(checklist_path):
        return checklist_path

    # Fallback: first available checklist
    ref_dir = os.path.join(config.skill_dir, "reference")
    for name in ("checklist-c-cpp.md", "checklist-go.md", "checklist-rust.md", "checklist-managed.md"):
        path = os.path.join(ref_dir, name)
        if os.path.exists(path):
            return path

    return ""


async def _run_entry_point(
    ep: EntryPoint,
    config: AuditConfig,
    checkpoint: CheckpointManager,
    stage1_output: str,
    checklist_path: str,
) -> list[str]:
    """
    Run analysis for one entry point. Returns list of finding file paths written.
    """
    key = _task_key(ep)
    result_dir = os.path.join(config.output_dir, "stage-3-details")

    if checkpoint.is_complete(key):
        logger.info(f"Stage 3: {ep.module_id}/{ep.id} already complete, skipping.")
        # Collect existing finding files for this EP
        pattern = os.path.join(result_dir, f"{ep.module_id}-{ep.id}-F-*.md")
        return sorted(glob.glob(pattern))

    logger.info(f"Stage 3: Analyzing {ep.module_id}/{ep.id} ({ep.type} at {ep.location})...")

    # Build the finding file prefix for this EP
    finding_prefix = f"{ep.module_id}-{ep.id}"

    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "stage3.md")
    prompt = load_prompt(
        prompt_path,
        stage1_output_path=stage1_output,
        ep_block=ep.raw_block,
        module_id=ep.module_id,
        ep_id=ep.id,
        ep_type=ep.type,
        location=ep.location,
        attacker_controlled_data=ep.attacker_controlled_data,
        initial_validation=ep.initial_validation or "None observed",
        analysis_hints=ep.analysis_hints,
        result_dir=result_dir,
        finding_prefix=finding_prefix,
        skill_dir=config.skill_dir,
        checklist_path=checklist_path,
        target_path=config.target,
    )

    # For Stage 3, there may be 0 or more output files.
    # We validate each finding file individually after the agent completes.
    validator = os.path.join(config.skill_dir, "script", "validate_stage3.py")

    # Run the agent (no single output path — agent writes N files)
    from ..agent_utils import run_agent
    await run_agent(prompt, cwd=config.target)

    # Collect and validate all finding files written for this EP
    pattern = os.path.join(result_dir, f"{finding_prefix}-F-*.md")
    finding_files = sorted(glob.glob(pattern))

    validated_files = []
    for fpath in finding_files:
        result = run_validator(validator, fpath)
        if result.returncode != 0:
            logger.warning(f"Stage 3: Validation failed for {fpath}:\n{result.stdout}")
            # Attempt repair (one pass)
            issues = result.stdout.strip()
            repair_prompt = (
                f"The finding file at `{fpath}` failed validation. "
                f"Please fix all issues listed below:\n\n"
                f"```\n{issues}\n```"
            )
            await run_agent(repair_prompt, cwd=config.target, max_turns=10)
            result2 = run_validator(validator, fpath)
            if result2.returncode != 0:
                logger.warning(f"Stage 3: Repair failed for {fpath}, keeping as-is.")
        validated_files.append(fpath)

    checkpoint.mark_complete(key)
    logger.info(f"Stage 3: {ep.module_id}/{ep.id} complete. Findings: {len(validated_files)}")
    return validated_files


async def run_stage3(
    ep_map: dict[str, list[EntryPoint]],
    config: AuditConfig,
    checkpoint: CheckpointManager,
) -> list[str]:
    """
    Run Stage 3 for all entry points in parallel.
    Returns list of all finding file paths across all EPs.
    """
    stage1_output = os.path.join(config.output_dir, "stage-1-scope.md")
    checklist_path = _detect_checklist(config)
    if checklist_path:
        logger.info(f"Stage 3: Using checklist: {checklist_path}")
    else:
        logger.warning("Stage 3: No checklist found — agents will proceed without one.")

    # Flatten all entry points
    all_eps = [ep for eps in ep_map.values() for ep in eps]
    if not all_eps:
        logger.warning("Stage 3: No entry points to analyze.")
        return []

    semaphore = asyncio.Semaphore(config.max_parallel)
    tasks = [
        _run_entry_point(ep, config, checkpoint, stage1_output, checklist_path)
        for ep in all_eps
    ]
    results = await run_parallel(tasks, semaphore)

    all_finding_files: list[str] = []
    for ep, result in zip(all_eps, results):
        if isinstance(result, Exception):
            logger.error(f"Stage 3: {ep.module_id}/{ep.id} failed with exception: {result}")
        else:
            all_finding_files.extend(result)

    logger.info(f"Stage 3 complete. Total finding files: {len(all_finding_files)}")
    return all_finding_files
