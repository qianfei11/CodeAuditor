import path from "node:path";

import { runParallelLimited, coerceError } from "../utils.js";
import { runWithValidation } from "../agents/index.js";
import { CheckpointManager } from "../checkpoint.js";
import type { AuditConfig, EntryPoint, Module } from "../config.js";
import { getLogger } from "../logger.js";
import { parseEntryPoints } from "../parsing/stage3.js";
import { loadPrompt } from "../prompts.js";
import { validateStage3File } from "../validation/stage3.js";

const logger = getLogger("stage3");

function taskKey(module: Module): string {
  return `stage3:${module.id}`;
}

async function runModule(
  module: Module,
  config: AuditConfig,
  checkpoint: CheckpointManager,
  stage2Output: string,
): Promise<EntryPoint[]> {
  const key = taskKey(module);
  const resultDir = path.join(config.outputDir, "stage-3-details");
  const outputPath = path.join(resultDir, `${module.id}.md`);

  if (checkpoint.isComplete(key)) {
    logger.info("Stage 3: %s already complete, loading existing output.", module.id);
    return parseEntryPoints(outputPath, module.id);
  }

  const prompt = await loadPrompt("stage3.md", {
    stage2_output_path: stage2Output,
    result_dir: resultDir,
    module_id: module.id,
  });

  const { passed } = await runWithValidation({
    config,
    prompt,
    cwd: config.target,
    outputPath,
    validator: validateStage3File,
  });

  if (!passed) {
    logger.warning("Stage 3: %s validation did not fully pass.", module.id);
  }

  checkpoint.markComplete(key);
  const entryPoints = parseEntryPoints(outputPath, module.id);
  logger.info(
    "Stage 3: %s complete. Entry points: %s",
    module.id,
    entryPoints.map((entryPoint) => entryPoint.id).join(", "),
  );
  return entryPoints;
}

export async function runStage3(
  modules: Module[],
  config: AuditConfig,
  checkpoint: CheckpointManager,
): Promise<Record<string, EntryPoint[]>> {
  const stage2Output = path.join(config.outputDir, "stage-2-scope.md");
  const results = await runParallelLimited(modules, config.maxParallel, async (module) => {
    return await runModule(module, config, checkpoint, stage2Output);
  });

  const entryPointMap: Record<string, EntryPoint[]> = {};
  results.forEach((result, index) => {
    const module = modules[index];
    if (!module) {
      return;
    }
    if (result.status === "rejected") {
      logger.error("Stage 3: %s failed with exception: %s", module.id, coerceError(result.reason).message);
      entryPointMap[module.id] = [];
      return;
    }
    entryPointMap[module.id] = result.value;
  });

  return entryPointMap;
}
