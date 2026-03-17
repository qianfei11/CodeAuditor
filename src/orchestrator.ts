import path from "node:path";

import { CheckpointManager } from "./checkpoint.js";
import type { AuditConfig, EntryPoint, Module } from "./config.js";
import { getLogger } from "./logger.js";
import { getInScopeModules } from "./parsing/stage2.js";
import { parseEntryPoints } from "./parsing/stage3.js";
import { listMarkdownFiles } from "./utils.js";
import { runSetup } from "./stages/stage0.js";
import { runStage1 } from "./stages/stage1.js";
import { runStage2 } from "./stages/stage2.js";
import { runStage3 } from "./stages/stage3.js";
import { runStage4 } from "./stages/stage4.js";
import { runStage5 } from "./stages/stage5.js";
import { runStage6 } from "./stages/stage6.js";

const logger = getLogger("orchestrator");

export async function runAudit(config: AuditConfig): Promise<string> {
  const checkpoint = new CheckpointManager(config.outputDir, config.resume);

  if (config.resume) {
    logger.info("Resume mode enabled. Existing output files and markers will be reused.");
  }

  if (!config.skipStages.includes(0)) {
    await runSetup(config);
  }

  let instructionStage2Path: string;
  let instructionStage5Path: string;
  if (!config.skipStages.includes(1)) {
    const stage1 = await runStage1(config, checkpoint);
    instructionStage2Path = stage1.instructionStage2Path;
    instructionStage5Path = stage1.instructionStage5Path;
  } else {
    logger.info("Stage 1 skipped.");
    instructionStage2Path = path.join(config.outputDir, "stage-1-details", "instruction-stage2.md");
    instructionStage5Path = path.join(config.outputDir, "stage-1-details", "instruction-stage5.md");
  }

  let modules: Module[] = [];
  if (!config.skipStages.includes(2)) {
    modules = await runStage2(config, checkpoint, instructionStage2Path);
  } else {
    logger.info("Stage 2 skipped.");
    modules = getInScopeModules(path.join(config.outputDir, "stage-2-scope.md"));
  }

  if (modules.length === 0) {
    throw new Error("Stage 2 produced no in-scope modules.");
  }

  let entryPointMap: Record<string, EntryPoint[]> = {};
  if (!config.skipStages.includes(3)) {
    entryPointMap = await runStage3(modules, config, checkpoint);
  } else {
    logger.info("Stage 3 skipped.");
    const stage3Dir = path.join(config.outputDir, "stage-3-details");
    for (const module of modules) {
      const filePath = path.join(stage3Dir, `${module.id}.md`);
      entryPointMap[module.id] = parseEntryPoints(filePath, module.id);
    }
  }

  let findingFiles: string[] = [];
  if (!config.skipStages.includes(4)) {
    findingFiles = await runStage4(entryPointMap, config, checkpoint);
  } else {
    logger.info("Stage 4 skipped.");
    findingFiles = await listMarkdownFiles(path.join(config.outputDir, "stage-4-details"));
  }

  if (!config.skipStages.includes(5)) {
    await runStage5(findingFiles, config, checkpoint, instructionStage5Path);
  } else {
    logger.info("Stage 5 skipped.");
  }

  let reportPath = "";
  if (!config.skipStages.includes(6)) {
    reportPath = await runStage6(config, checkpoint);
  } else {
    logger.info("Stage 6 skipped.");
  }

  logger.info("Audit complete. Report: %s", reportPath);
  return reportPath;
}
