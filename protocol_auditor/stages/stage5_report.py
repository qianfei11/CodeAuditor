"""Stage 5: Report Generation — subprocess call to generate_report.py."""

import logging
import os
import subprocess

from ..checkpoint import CheckpointManager
from ..config import AuditConfig

logger = logging.getLogger(__name__)

TASK_KEY = "stage5"


def run_stage5(config: AuditConfig, checkpoint: CheckpointManager) -> str:
    """
    Run Stage 5: generate the final report.
    Returns the path to report.md.
    """
    report_path = os.path.join(config.output_dir, "report.md")

    if checkpoint.is_complete(TASK_KEY):
        logger.info("Stage 5 already complete.")
        return report_path

    logger.info("Stage 5: Generating final report...")

    script_path = os.path.join(config.skill_dir, "script", "generate_report.py")
    stage1_scope = os.path.join(config.output_dir, "stage-1-scope.md")
    stage4_dir = os.path.join(config.output_dir, "stage-4-details")

    result = subprocess.run(
        [
            "python3", script_path,
            "--stage1-scope", stage1_scope,
            "--stage4-dir", stage4_dir,
            "--output", report_path,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error(f"Stage 5: generate_report.py failed:\n{result.stderr}")
        raise RuntimeError(f"Report generation failed: {result.stderr}")

    if not os.path.exists(report_path) or os.path.getsize(report_path) == 0:
        raise RuntimeError(f"Report file missing or empty: {report_path}")

    logger.info(f"Stage 5 complete. Report: {report_path}")
    if result.stdout:
        logger.info(result.stdout.strip())

    checkpoint.mark_complete(TASK_KEY)
    return report_path
