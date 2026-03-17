# Stage 1: Research and Threat Model

You are performing **Stage 1** of an orchestrated network protocol security audit. Write your research report to disk; do not print it in your response.

## Your Task

Research the project at **__TARGET_PATH__** and produce a vulnerability research and threat model report at **__OUTPUT_PATH__**.

- **Date window**: __START_DATE__ through __TODAY__ (last 5 years)
- **Severity filter**: Critical and High; include Medium if the result set is sparse
- **Vulnerability limit**: at most 10 public entries; preserve coverage of recurring patterns over near-duplicate entries

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
- Which bug classes the project considers security vulnerabilities
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

Collect up to 10 of the most recent public vulnerabilities within the date window that meet the severity filter. For each item, capture: disclosure date, identifier (CVE, GHSA, or advisory ID), short title, affected versions/components, fixed version or mitigation, severity or CVSS, and canonical source URL.

Sort by disclosure date descending. Deduplicate entries that appear on multiple pages. Exclude dependency CVEs unless the project's own sources present them as vulnerabilities in the project itself.

### Step 4: Web CVE and Advisory Search

Use this step when the official site does not provide a usable advisory list or when the first-party list is clearly incomplete.

Search with the project's exact product name, repository name, maintainer, and common aliases. Prefer exact matches to avoid false positives for products with generic names. Reject hits that belong to a different product with a similar name.

Search sources in this order:
1. GitHub Security Advisories
2. NVD or CVE records
3. Vendor advisories or trusted security mailing lists

Stop after collecting 10 relevant vulnerabilities inside the date window.

### Step 5: Write Output

Write your report to **__OUTPUT_PATH__** using the available file editing tools. The file must have this exact structure:

```markdown
# Research and Threat Model

## Project and Research Scope
(project path, name, language, brief description; date window __START_DATE__ through __TODAY__; severity filter applied)

## Security Policy and Disclosure Process
(findings from local documents; quote key scope language; "No security policy found." if absent)

## Threat Model Signals
(trust boundaries, attacker assumptions, deployment context, protected assets — sourced from repo docs or inferred from protocol role and deployment patterns)

## Recent Vulnerabilities

| Date | ID | Summary | Affected | Fixed | Severity | Source |
| --- | --- | --- | --- | --- | --- | --- |

## Threat Model Conclusions

### Attacker Profile
(network-based / local / both; authentication assumed; privilege required; deployment assumptions)

### Priority Vulnerability Classes
(vulnerability classes that should receive extra scrutiny during code audit, based on historical patterns and the protocol's attack surface — one bullet per class with a brief justification citing evidence)

### Out of Scope
(issues that are out of scope for this audit, with justification — e.g., post-auth DoS only, dependency-only CVEs not affecting the project itself, client-side issues if only server is in scope)

### High-Risk Modules and Subsystems
(modules or subsystems that recur most often in the vulnerability set, or that have the highest network-facing attack exposure — these should be prioritized in Stage 2 scoping)

## Vulnerability Patterns for Follow-On Audit
(short watchlist of recurring weakness types, exposed trust boundaries, or operational themes to prioritize in the code audit)

## Gaps and Limitations
(data quality issues, missing version info, ambiguous product aliases, no public vulnerability history found, etc.)

## Sources
(URLs used, one per line)
```

**IMPORTANT**: Write the output to **__OUTPUT_PATH__** using the available file editing tools. Do not return the content in your response.

Prefer precise dates over relative time phrases. Separate facts from inference. Distinguish "no public vulnerabilities found" from "no evidence available." Attach a source URL to every important claim.

## Completion Checklist

- [ ] Project name, language, and maintainer identified
- [ ] Local security documents inspected (or noted as absent)
- [ ] First-party advisory links followed
- [ ] Web CVE/advisory search completed if first-party list is missing or sparse
- [ ] Report written to **__OUTPUT_PATH__** with all required sections
- [ ] Threat Model Conclusions section is present and substantive, with Priority Vulnerability Classes and Out of Scope subsections
