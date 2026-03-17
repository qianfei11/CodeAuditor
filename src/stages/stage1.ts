import path from "node:path";

import { runWithValidation } from "../agents/index.js";
import { CheckpointManager } from "../checkpoint.js";
import type { AuditConfig } from "../config.js";
import { getLogger } from "../logger.js";
import { loadPrompt } from "../prompts.js";
import { validateStage1File } from "../validation/stage1.js";

const logger = getLogger("stage1");
const TASK_KEY = "stage1";

export async function runStage1(
  config: AuditConfig,
  checkpoint: CheckpointManager,
): Promise<string> {
  const outputPath = path.join(config.outputDir, "stage-1-research.md");

  if (checkpoint.isComplete(TASK_KEY)) {
    logger.info("Stage 1 already complete, loading existing output.");
    return outputPath;
  }

  const today = new Date().toISOString().slice(0, 10);
  const startDate = new Date(Date.now() - 5 * 365.25 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10);

  const prompt = await loadPrompt("stage1.md", {
    target_path: config.target,
    output_path: outputPath,
    today,
    start_date: startDate,
    user_instructions: config.scope || "No additional scope constraints.",
  });

  const { passed } = await runWithValidation({
    config,
    prompt,
    cwd: config.target,
    outputPath,
    validator: validateStage1File,
  });

  if (!passed) {
    logger.warning("Stage 1 validation did not fully pass, continuing with best-effort output.");
  }

  checkpoint.markComplete(TASK_KEY);
  logger.info("Stage 1 complete. Research report: %s", outputPath);
  return outputPath;
}
