import type { ValidationIssue } from "../config.js";

import { findSection, readFileOrIssues } from "./common.js";

export function validateStage1File(filePath: string): ValidationIssue[] {
  const { content, issues } = readFileOrIssues(filePath);
  if (issues.length > 0) {
    return issues;
  }

  if (!content.trim()) {
    return [
      {
        description: "Output file is empty.",
        expected: "A markdown research report with required sections.",
        fix: "Write the full Stage 1 research report to this file.",
      },
    ];
  }

  const validationIssues: ValidationIssue[] = [];

  for (const sectionName of [
    "Project and Research Scope",
    "Threat Model Signals",
    "Recent Vulnerabilities",
    "Vulnerability Patterns for Follow-On Audit",
  ]) {
    const section = findSection(content, sectionName);
    if (section === null) {
      validationIssues.push({
        description: `Missing required section: "## ${sectionName}"`,
        expected: `A "## ${sectionName}" heading must be present.`,
        fix: `Add a "## ${sectionName}" section with appropriate content.`,
      });
      continue;
    }

    if (!section.trim()) {
      validationIssues.push({
        description: `Section "## ${sectionName}" is empty.`,
        expected: "This section must contain content.",
        fix: `Fill in the ${sectionName} section with the relevant information.`,
      });
    }
  }

  const threatModelSection = findSection(content, "Threat Model Signals");
  if (threatModelSection !== null) {
    for (const subsection of [
      "Attacker Profile",
      "Historical Vulnerability Patterns",
      "Priority Vulnerability Classes",
      "High-Risk Modules and Subsystems",
      "Severity Distribution and Calibration",
    ]) {
      if (!threatModelSection.includes(subsection)) {
        validationIssues.push({
          description: `Threat Model Signals is missing subsection: "${subsection}"`,
          expected: `A "### ${subsection}" subsection inside Threat Model Signals.`,
          fix: `Add a "### ${subsection}" subsection to the Threat Model Signals section.`,
        });
      }
    }
  }

  return validationIssues;
}
