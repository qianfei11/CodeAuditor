"""Stage 0: Setup — create output directories and initialize checkpoint."""

import logging
import os

from ..checkpoint import CheckpointManager
from ..config import AuditConfig

logger = logging.getLogger(__name__)


def run_setup(config: AuditConfig, checkpoint: CheckpointManager):
    """Create output directory structure and initialize checkpoint."""
    dirs = [
        config.output_dir,
        os.path.join(config.output_dir, "stage-2-details"),
        os.path.join(config.output_dir, "stage-3-details"),
        os.path.join(config.output_dir, "stage-4-details"),
        os.path.join(config.output_dir, "stage-4-details", "_pending"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        logger.debug(f"Directory ready: {d}")

    # Persist config in checkpoint
    checkpoint.set_config({
        "target": config.target,
        "output_dir": config.output_dir,
        "skill_dir": config.skill_dir,
        "max_parallel": config.max_parallel,
        "threat_model": config.threat_model,
        "scope": config.scope,
    })
    logger.info(f"Stage 0 complete. Output dir: {config.output_dir}")
