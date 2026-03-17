import path from "node:path";

import { runAgent } from "../agents/index.js";
import { CheckpointManager } from "../checkpoint.js";
import type { AuditConfig, EntryPoint } from "../config.js";
import { getLogger } from "../logger.js";
import { loadPrompt } from "../prompts.js";
import { coerceError, formatValidationIssues, listMatchingFiles, runParallelLimited } from "../utils.js";
import { validateStage4File } from "../validation/stage4.js";

const logger = getLogger("stage4");

function taskKey(entryPoint: EntryPoint): string {
  return `stage4:${entryPoint.moduleId}:${entryPoint.id}`;
}

async function runEntryPoint(
  entryPoint: EntryPoint,
  config: AuditConfig,
  checkpoint: CheckpointManager,
): Promise<string[]> {
  const key = taskKey(entryPoint);
  const resultDir = path.join(config.outputDir, "stage-4-details");
  const findingPrefix = `${entryPoint.moduleId}-${entryPoint.id}`;
  const findingPattern = new RegExp(`^${findingPrefix}-F-\\d+\\.md$`);

  if (checkpoint.isComplete(key)) {
    logger.info("Stage 4: %s/%s already complete, skipping.", entryPoint.moduleId, entryPoint.id);
    return await listMatchingFiles(resultDir, findingPattern);
  }

  const prompt = await loadPrompt("stage4.md", {
    ep_block: entryPoint.rawBlock,
    module_id: entryPoint.moduleId,
    ep_id: entryPoint.id,
    ep_type: entryPoint.type,
    location: entryPoint.location,
    attacker_controlled_data: entryPoint.attackerControlledData,
    initial_validation: entryPoint.initialValidation || "None observed",
    analysis_hints: entryPoint.analysisHints,
    result_dir: resultDir,
    finding_prefix: findingPrefix,
    target_path: config.target,
  });

  await runAgent({
    prompt,
    config,
    cwd: config.target,
  });

  const findingFiles = await listMatchingFiles(resultDir, findingPattern);
  for (const findingFile of findingFiles) {
    let issues = validateStage4File(findingFile);
    if (issues.length === 0) {
      continue;
    }

    logger.warning("Stage 4: Validation failed for %s\n%s", findingFile, formatValidationIssues(issues));
    const repairPrompt =
      `The finding file at \`${findingFile}\` failed validation. ` +
      `Please fix all issues listed below:\n\n\`\`\`\n${formatValidationIssues(issues)}\n\`\`\``;

    await runAgent({
      prompt: repairPrompt,
      config,
      cwd: config.target,
      maxTurns: 10,
    });

    issues = validateStage4File(findingFile);
    if (issues.length > 0) {
      logger.warning("Stage 4: Repair failed for %s\n%s", findingFile, formatValidationIssues(issues));
    }
  }

  checkpoint.markComplete(key);
  logger.info("Stage 4: %s/%s complete. Findings: %s", entryPoint.moduleId, entryPoint.id, findingFiles.length);
  return findingFiles;
}

export async function runStage4(
  entryPointMap: Record<string, EntryPoint[]>,
  config: AuditConfig,
  checkpoint: CheckpointManager,
): Promise<string[]> {
  const allEntryPoints = Object.values(entryPointMap).flat();
  if (allEntryPoints.length === 0) {
    logger.warning("Stage 4: No entry points to analyze.");
    return [];
  }

  const results = await runParallelLimited(allEntryPoints, config.maxParallel, async (entryPoint) => {
    return await runEntryPoint(entryPoint, config, checkpoint);
  });

  const allFindingFiles: string[] = [];
  results.forEach((result, index) => {
    const entryPoint = allEntryPoints[index];
    if (!entryPoint) {
      return;
    }
    if (result.status === "rejected") {
      logger.error(
        "Stage 4: %s/%s failed with exception: %s",
        entryPoint.moduleId,
        entryPoint.id,
        coerceError(result.reason).message,
      );
      return;
    }
    allFindingFiles.push(...result.value);
  });

  logger.info("Stage 4 complete. Total finding files: %s", allFindingFiles.length);
  return allFindingFiles;
}
