import path from "node:path";

import { runWithValidation } from "../agents/index.js";
import { CheckpointManager } from "../checkpoint.js";
import type { AuditConfig, Module } from "../config.js";
import { getLogger } from "../logger.js";
import { getInScopeModules } from "../parsing/stage2.js";
import { loadPrompt } from "../prompts.js";
import { validateStage2File } from "../validation/stage2.js";

const logger = getLogger("stage2");
const TASK_KEY = "stage2";

export async function runStage2(
  config: AuditConfig,
  checkpoint: CheckpointManager,
  researchPath: string,
): Promise<Module[]> {
  const outputPath = path.join(config.outputDir, "stage-2-scope.md");

  if (checkpoint.isComplete(TASK_KEY)) {
    logger.info("Stage 2 already complete, loading existing output.");
    return getInScopeModules(outputPath);
  }

  const prompt = await loadPrompt("stage2.md", {
    target_path: config.target,
    output_path: outputPath,
    research_path: researchPath,
    threat_model: config.threatModel,
    user_instructions: config.scope || "No additional scope constraints.",
  });

  const { passed } = await runWithValidation({
    config,
    prompt,
    cwd: config.target,
    outputPath,
    validator: validateStage2File,
  });

  if (!passed) {
    logger.warning("Stage 2 validation did not fully pass, continuing with best-effort output.");
  }

  checkpoint.markComplete(TASK_KEY);
  const modules = getInScopeModules(outputPath);
  logger.info("Stage 2 complete. In-scope modules: %s", modules.map((module) => module.id).join(", "));
  return modules;
}
