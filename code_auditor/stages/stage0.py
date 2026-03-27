from __future__ import annotations

import os

from ..config import AuditConfig
from ..logger import get_logger

logger = get_logger("stage0")


async def run_setup(config: AuditConfig) -> None:
    directories = [
        config.output_dir,
        os.path.join(config.output_dir, ".markers"),
        os.path.join(config.output_dir, "stage-2-details"),
        os.path.join(config.output_dir, "stage-3-details"),
        os.path.join(config.output_dir, "stage-4-details"),
        os.path.join(config.output_dir, "stage-5-details"),
        os.path.join(config.output_dir, "stage-5-details", "_pending"),
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.debug("Directory ready: %s", directory)

    logger.info("Stage 0 complete. Output dir: %s", config.output_dir)
