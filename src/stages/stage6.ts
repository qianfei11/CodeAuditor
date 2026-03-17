import fs from "node:fs/promises";
import path from "node:path";

import { CheckpointManager } from "../checkpoint.js";
import type { AuditConfig } from "../config.js";
import { getLogger } from "../logger.js";
import { generateReport } from "../report/generate.js";

const logger = getLogger("stage6");
const TASK_KEY = "stage6";

export async function runStage6(
  config: AuditConfig,
  checkpoint: CheckpointManager,
): Promise<string> {
  const reportPath = path.join(config.outputDir, "report.md");

  if (checkpoint.isComplete(TASK_KEY)) {
    logger.info("Stage 6 already complete.");
    return reportPath;
  }

  const stage2Scope = path.join(config.outputDir, "stage-2-scope.md");
  const stage5Dir = path.join(config.outputDir, "stage-5-details");
  const summary = generateReport(stage2Scope, stage5Dir, reportPath);
  const stat = await fs.stat(reportPath);
  if (stat.size === 0) {
    throw new Error(`Report file missing or empty: ${reportPath}`);
  }

  checkpoint.markComplete(TASK_KEY);
  logger.info("Stage 6 complete. Report: %s", reportPath);
  logger.info("Report summary: total=%s severities=%j", summary.totalFindings, summary.severityCounts);
  return reportPath;
}
