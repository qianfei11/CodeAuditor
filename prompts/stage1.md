# Stage 1: Research and Threat Model

You are performing **Stage 1** of an orchestrated network protocol security audit. Write all output files to disk; do not print content in your response.

## Your Task

Research the project at **__TARGET_PATH__** and produce three output files:

1. **Research report** (user-facing summary): **__OUTPUT_PATH__**
2. **Stage 2 instruction** (module prioritization guidance): **__INSTRUCTION_STAGE2_PATH__**
3. **Stage 5 instruction** (severity evaluation context): **__INSTRUCTION_STAGE5_PATH__**

- **Date window**: __START_DATE__ through __TODAY__ (last 5 years)
- **Severity filter**: Critical and High; include Medium if the result set is sparse
- **Vulnerability coverage**: collect **all** qualifying public entries within the date window — do not cap the count

## User Instructions

__USER_INSTRUCTIONS__

## Workflow

### Step 1: Identify the Project

Determine the canonical project name, repository name, maintainer or organization name, and primary programming language from the source at **__TARGET_PATH__**.

### Step 2: Inspect Local Security and Disclosure Documents

Search the repository for dedicated security or disclosure documents. Useful filename patterns:

```bash
rg --files "__TARGET_PATH__" | rg -i '(^|/)(SECURITY(\.[^/]+)?|BUG(\.[^/]+)?|VULN(ERABILIT(Y|IES))?(\.[^/]+)?|ADVISOR(Y|IES)(\.[^/]+)?|DISCLOSURE(\.[^/]+)?|security\.txt)$'
```

If dedicated files are absent, scan `README*`, `CONTRIBUTING*`, and `docs/` for sections on security, vulnerabilities, threat models, attack surfaces, or trust boundaries.

Extract:
- Which bug classes the project explicitly considers security vulnerabilities
- Which issues are explicitly out of scope
- How maintainers want vulnerabilities reported
- Whether the project publishes advisories or a vulnerability archive
- Threat model language: trust boundaries, attacker assumptions, deployment assumptions, protected assets
- Links to official security pages, advisories, mailing lists, or bug bounty programs

If no repository security policy or threat model material exists, note that in the report and continue.

### Step 3: Follow First-Party Security and Advisory Links

Open any URLs discovered in Step 2 before doing generic web search. Priority order:

1. Official security pages
2. Official advisory archives
3. Official release notes or changelogs with security sections
4. Official blogs or mailing lists used for security announcements

Collect **all** public vulnerabilities within the date window that meet the severity filter. For each entry capture: disclosure date, identifier (CVE, GHSA, or advisory ID), short title, affected versions/components, fixed version or mitigation, severity label, CVSS score (if available), and canonical source URL. Also capture the full advisory or CVE description text — you will use this in the report.

Sort by disclosure date descending. Deduplicate entries that appear on multiple sources. Exclude dependency CVEs unless the project's own sources present them as vulnerabilities in the project itself.

### Step 4: Web CVE and Advisory Search

Use this step when the official site does not provide a usable advisory list or when the first-party list is clearly incomplete. Collect **all** matching entries — do not stop at any fixed count.

Search with the project's exact product name, repository name, maintainer, and common aliases. Prefer exact matches to avoid false positives for products with generic names. Reject hits that belong to a different product with a similar name.

Search sources in this order:
1. GitHub Security Advisories
2. NVD or CVE records
3. Vendor advisories or trusted security mailing lists

### Step 5: Write the Research Report

Write a complete, detailed report to **__OUTPUT_PATH__** using the available file editing tools. This file is the primary human-readable output. The file must have this exact structure:

```markdown
# Research and Threat Model

## Project and Research Scope
(project path, name, language, brief description; date window __START_DATE__ through __TODAY__; severity filter applied; total vulnerabilities collected)

## Security Policy and Disclosure Process
(findings from local documents; quote key scope language verbatim where relevant; note which bug classes the project explicitly considers in-scope or out-of-scope; "No security policy found." if absent)

## Threat Model Signals

### Attack Surface and Deployment Context
(where attacker-controlled input enters the system; network-facing interfaces and protocols; typical deployment models; trust boundaries between components; what the project protects)

### Attacker Profile
(characterize the attacker based on the vulnerability history and any explicit project security claims: network-based vs local; pre-authentication vs post-authentication; privilege level required; what percentage of historical CVEs were pre-auth or required no special access)

### Historical Vulnerability Patterns
(analyze the full vulnerability set to identify recurring themes: which CWE classes appear most often; which subsystems or components are repeatedly implicated; what exploitation techniques have been used; note any multi-year trends or shifts in bug class distribution)

### Priority Vulnerability Classes
(rank the bug classes most likely to appear in this codebase, derived from historical frequency combined with the protocol's inherent attack surface; for each class give a one-line justification citing specific CVEs or advisory patterns as evidence)

### High-Risk Modules and Subsystems
(list the specific modules, components, or directories that appear most frequently in the CVE/advisory history, or that have the broadest network-facing attack exposure based on the protocol structure; justify each with evidence)

### Severity Distribution and Calibration
(summarize the historical severity distribution: how many Critical / High / Medium findings, typical CVSS score ranges for this project/protocol; note any factors that have consistently driven scores up or down — e.g., pre-auth reachability, memory corruption leading to RCE, crash-only impact)

## Recent Vulnerabilities

| Date | ID | Title | Affected | Fixed | Severity | CVSS | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |

(one row per vulnerability, sorted by date descending)

### Vulnerability Descriptions

For each vulnerability in the table above, write a subsection:

#### [ID]: Title
(2–5 sentences: the full advisory or CVE description; what component was affected; the root cause or bug class; what an attacker could achieve; any notable exploitation conditions such as pre-auth reachability or specific configuration required)

## Vulnerability Patterns for Follow-On Audit
(a synthesized watchlist of recurring weakness types, exposed trust boundaries, and operational themes to prioritize in the code audit — derived from both the vulnerability history and the protocol's structural attack surface; each item should be a concrete, actionable pattern rather than a generic category)

## Sources
(URLs used, one per line)
```

Separate facts from inference. Label inferences explicitly (e.g., "inferred from CVE pattern" or "stated in SECURITY.md"). Attach a source URL to every important claim. Use precise dates, not relative phrases.

### Step 6: Write the Stage 2 Instruction File

Write a concise, actionable instruction to **__INSTRUCTION_STAGE2_PATH__** that will be loaded into the Stage 2 agent's context window. Keep this file short — it is injected into an agent prompt, not read by a human. Derive its content from the vulnerability history and security claims synthesized in the research report.

The file must use this exact structure:

```markdown
# Stage 2 Guidance: Module Prioritization

## High-Risk Modules to Prioritize
(list specific module names, directories, or subsystems that appear most in the CVE/advisory history or have the broadest network-facing attack surface; Stage 2 should default these to "Yes" for analysis — cite the evidence briefly for each)

## Vulnerability Classes That Drive Module Selection
(concise list of the bug classes most historically relevant to this project, derived from the CVE pattern analysis; Stage 2 should mark modules containing these code patterns as in-scope)

## Attacker Entry Points
(the network-facing interfaces and message types through which an unauthenticated or low-privilege attacker reaches the code, inferred from the protocol structure and historical exploitation patterns; helps Stage 2 identify which modules handle these paths)
```

### Step 7: Write the Stage 5 Instruction File

Write a concise, actionable instruction to **__INSTRUCTION_STAGE5_PATH__** that will be loaded into the Stage 5 agent's context window to help it evaluate the severity of confirmed vulnerabilities. Keep this file short — it is injected into an agent prompt, not read by a human. Derive its content from the historical severity distribution and attacker profile established in the research report.

The file must use this exact structure:

```markdown
# Stage 5 Guidance: Severity Evaluation

## Attacker Profile
(two or three sentences: who the attacker is, their network position, and what authentication/privilege they hold before exploitation — inferred from historical CVE patterns and any explicit project security claims)

## Historical Severity Benchmarks
(the actual CVSS score ranges and severity labels observed for this project/protocol historically; use these as calibration anchors — e.g., "pre-auth memory corruption has historically been scored 9.x Critical", "DoS-only findings have been scored 5.x–7.5")

## High-Impact Vulnerability Classes
(classes most likely to yield Critical or High findings for this project, with a one-line reason each, grounded in the historical record)

## Severity Modifiers
(factors that have consistently raised or lowered severity in this project's history — e.g., "pre-auth reachability pushes all scores to High or above", "crash-only findings without heap corruption have been capped at Medium")
```

## Completion Checklist

- [ ] Project name, language, and maintainer identified
- [ ] Local security documents inspected (or noted as absent)
- [ ] First-party advisory links followed; all qualifying vulnerabilities collected
- [ ] Web CVE/advisory search completed if first-party list is missing or sparse
- [ ] Research report written to **__OUTPUT_PATH__** with all required sections
- [ ] Threat Model Signals section is detailed and evidence-driven, with all subsections present
- [ ] Each vulnerability has a description entry under "Vulnerability Descriptions"
- [ ] Stage 2 instruction written to **__INSTRUCTION_STAGE2_PATH__**
- [ ] Stage 5 instruction written to **__INSTRUCTION_STAGE5_PATH__**
