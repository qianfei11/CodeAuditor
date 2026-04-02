from __future__ import annotations

import os
import re

from .checkpoint import CheckpointManager
from .config import AnalysisUnit, AuditConfig, Module
from .logger import get_logger
from .parsing.stage2 import parse_modules
from .stages.stage0 import run_setup
from .stages.stage1 import Stage1Output, run_stage1
from .stages.stage2 import run_stage2
from .stages.stage3 import run_stage3
from .stages.stage4 import run_stage4
from .stages.stage5 import run_stage5
from .stages.stage6 import run_stage6
from .utils import list_json_files

logger = get_logger("orchestrator")


async def run_audit(config: AuditConfig) -> str:
    checkpoint = CheckpointManager(config.output_dir, config.resume)

    if config.resume:
        logger.info("Resume mode enabled. Existing output files and markers will be reused.")

    # Stage 0: setup
    if 0 not in config.skip_stages:
        await run_setup(config)

    # Stage 1: security context research
    stage1_out: Stage1Output | None = None
    if 1 not in config.skip_stages:
        stage1_out = await run_stage1(config, checkpoint)

    # Pause for user review before continuing
    if 1 not in config.skip_stages and not all(s in config.skip_stages for s in range(2, 7)):
        details_dir_preview = os.path.join(config.output_dir, "stage-1-details")
        logger.info(
            "Stage 1 complete. Review generated files in: %s", details_dir_preview
        )
        input("\nPress Enter to continue to the next stages...")

    # Resolve directive paths (from stage1 output or default locations)
    details_dir = os.path.join(config.output_dir, "stage-1-details")
    auditing_focus_path = (
        stage1_out.auditing_focus_path if stage1_out
        else os.path.join(details_dir, "auditing-focus.md")
    )
    vuln_criteria_path = (
        stage1_out.vuln_criteria_path if stage1_out
        else os.path.join(details_dir, "vulnerability-criteria.md")
    )

    # Stage 2: decompose project into modules
    modules: list[Module] = []
    if 2 not in config.skip_stages:
        modules = await run_stage2(config, checkpoint)
    elif 3 not in config.skip_stages:
        logger.info("Stage 2 skipped. Loading existing modules.")
        modules = parse_modules(os.path.join(config.output_dir, "stage-2-modules.json"))
    else:
        logger.info("Stage 2 skipped.")

    if not modules and 3 not in config.skip_stages:
        raise RuntimeError("Stage 2 produced no modules.")

    # Stage 3: assess scale and define analysis units
    analysis_units: list[AnalysisUnit] = []
    if 3 not in config.skip_stages:
        analysis_units = await run_stage3(modules, config, checkpoint)
    else:
        logger.info("Stage 3 skipped.")
        stage3_dir = os.path.join(config.output_dir, "stage-3-details")
        au_files = sorted(
            f for f in list_json_files(stage3_dir) if re.search(r"[\\/]AU-\d+\.json$", f)
        )
        for au_file_path in au_files:
            m = re.search(r"AU-(\d+)\.json$", au_file_path)
            if m:
                analysis_units.append(AnalysisUnit(id=f"AU-{m.group(1)}", module_id="", au_file_path=au_file_path))

    # Stage 4: bug discovery per AU
    bug_files: list[str] = []
    if 4 not in config.skip_stages:
        bug_files = await run_stage4(
            analysis_units, config, checkpoint,
            auditing_focus_path, vuln_criteria_path,
        )
    else:
        logger.info("Stage 4 skipped.")
        bug_files = list_json_files(os.path.join(config.output_dir, "stage-4-details"))

    # Stage 5: evaluate findings
    if 5 not in config.skip_stages:
        await run_stage5(bug_files, config, checkpoint, vuln_criteria_path)
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
