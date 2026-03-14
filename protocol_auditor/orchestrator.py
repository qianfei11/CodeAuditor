"""Main pipeline controller — sequences stages, manages checkpoint."""

import logging

from .checkpoint import CheckpointManager
from .config import AuditConfig
from .stages.stage0_setup import run_setup
from .stages.stage1_scope import run_stage1
from .stages.stage2_entry_points import run_stage2
from .stages.stage3_analysis import run_stage3
from .stages.stage4_evaluation import run_stage4
from .stages.stage5_report import run_stage5

logger = logging.getLogger(__name__)


async def run_audit(config: AuditConfig) -> str:
    """
    Execute the full audit pipeline.
    Returns path to the final report.
    """
    checkpoint = CheckpointManager(config.output_dir)

    if config.resume:
        if checkpoint.load():
            logger.info("Resuming from checkpoint.")
        else:
            logger.info("No checkpoint found, starting fresh.")

    # Stage 0: Setup
    if 0 not in config.skip_stages:
        run_setup(config, checkpoint)

    # Stage 1: Orient and Scope
    modules = []
    if 1 not in config.skip_stages:
        modules = await run_stage1(config, checkpoint)
    else:
        logger.info("Stage 1 skipped.")
        # Still need modules for subsequent stages
        from .parsing.stage1_parser import get_in_scope_modules
        import os
        stage1_path = os.path.join(config.output_dir, "stage-1-scope.md")
        modules = get_in_scope_modules(stage1_path)

    if not modules:
        logger.error("No in-scope modules found. Aborting.")
        raise RuntimeError("Stage 1 produced no in-scope modules.")

    # Stage 2: Entry Point Identification
    ep_map = {}
    if 2 not in config.skip_stages:
        ep_map = await run_stage2(modules, config, checkpoint)
    else:
        logger.info("Stage 2 skipped.")
        # Reconstruct ep_map from existing files
        import os
        from .parsing.stage2_parser import parse_entry_points
        stage2_dir = os.path.join(config.output_dir, "stage-2-details")
        for module in modules:
            path = os.path.join(stage2_dir, f"{module.id}.md")
            if os.path.exists(path):
                ep_map[module.id] = parse_entry_points(path, module.id)

    # Stage 3: Vulnerability Analysis
    finding_files = []
    if 3 not in config.skip_stages:
        finding_files = await run_stage3(ep_map, config, checkpoint)
    else:
        logger.info("Stage 3 skipped.")
        import glob
        import os
        pattern = os.path.join(config.output_dir, "stage-3-details", "*.md")
        finding_files = sorted(glob.glob(pattern))

    # Stage 4: Vulnerability Evaluation
    final_findings = []
    if 4 not in config.skip_stages:
        final_findings = await run_stage4(finding_files, config, checkpoint)
    else:
        logger.info("Stage 4 skipped.")

    # Stage 5: Report Generation
    report_path = ""
    if 5 not in config.skip_stages:
        report_path = run_stage5(config, checkpoint)
    else:
        logger.info("Stage 5 skipped.")

    logger.info(f"Audit complete. Report: {report_path}")
    return report_path
