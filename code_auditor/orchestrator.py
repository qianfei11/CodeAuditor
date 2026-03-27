from __future__ import annotations

import os
import re

from .checkpoint import CheckpointManager
from .config import AnalysisUnit, AuditConfig, Module
from .logger import get_logger
from .parsing.stage1 import parse_modules
from .stages.stage0 import run_setup
from .stages.stage1 import run_stage1
from .stages.stage2 import run_stage2
from .stages.stage3 import run_stage3
from .stages.stage4 import run_stage4
from .stages.stage5 import run_stage5
from .stages.stage6 import run_stage6
from .utils import list_json_files, list_markdown_files

logger = get_logger("orchestrator")


async def run_audit(config: AuditConfig) -> str:
    checkpoint = CheckpointManager(config.output_dir, config.resume)

    if config.resume:
        logger.info("Resume mode enabled. Existing output files and markers will be reused.")

    # Stage 0: setup
    if 0 not in config.skip_stages:
        await run_setup(config)

    # Stage 1: split project into functional modules
    modules: list[Module] = []
    if 1 not in config.skip_stages:
        modules = await run_stage1(config, checkpoint)
    else:
        logger.info("Stage 1 skipped.")
        modules = parse_modules(os.path.join(config.output_dir, "stage-1-modules.json"))

    if not modules:
        raise RuntimeError("Stage 1 produced no modules.")

    # Stage 2: assess scale and define analysis units
    analysis_units: list[AnalysisUnit] = []
    if 2 not in config.skip_stages:
        analysis_units = await run_stage2(modules, config, checkpoint)
    else:
        logger.info("Stage 2 skipped.")
        stage2_dir = os.path.join(config.output_dir, "stage-2-details")
        au_files = sorted(
            f for f in list_json_files(stage2_dir) if re.search(r"[\\/]AU-\d+\.json$", f)
        )
        for au_file_path in au_files:
            m = re.search(r"AU-(\d+)\.json$", au_file_path)
            if m:
                analysis_units.append(AnalysisUnit(id=f"AU-{m.group(1)}", module_id="", au_file_path=au_file_path))

    # Stage 3: analyze each unit for bugs and flaws
    bug_files: list[str] = []
    if 3 not in config.skip_stages:
        bug_files = await run_stage3(analysis_units, config, checkpoint)
    else:
        logger.info("Stage 3 skipped.")
        bug_files = list_json_files(os.path.join(config.output_dir, "stage-3-details"))

    # Stage 4: explore the threat model
    instruction_stage5_path: str
    if 4 not in config.skip_stages:
        stage4 = await run_stage4(config, checkpoint)
        instruction_stage5_path = stage4.instruction_stage5_path
    else:
        logger.info("Stage 4 skipped.")
        instruction_stage5_path = os.path.join(config.output_dir, "stage-4-details", "evaluation-guidance.md")

    # Stage 5: assess bugs against the threat model
    if 5 not in config.skip_stages:
        await run_stage5(bug_files, config, checkpoint, instruction_stage5_path)
    else:
        logger.info("Stage 5 skipped.")

    # Stage 6: generate report
    report_path = ""
    if 6 not in config.skip_stages:
        report_path = await run_stage6(config, checkpoint)
    else:
        logger.info("Stage 6 skipped.")

    logger.info("Audit complete. Report: %s", report_path)
    return report_path
