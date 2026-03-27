# Stage 4: Security Context Research

You are performing **Stage 4** of an orchestrated software security audit. Write your output to disk; do not print it in your response.

## Your Task

Research the project at **__TARGET_PATH__** and produce two documents:
1. A security context report summarizing the project's security posture, history, and threat landscape (for human review).
2. Distilled evaluation guidance for Stage 5 sub-agents who must decide which Stage 3 bugs are true security vulnerabilities and how severe they are.

- **Output file (security context)**: `__OUTPUT_PATH__`
- **Output file (Stage 5 evaluation guidance)**: `__INSTRUCTION_STAGE5_PATH__`
- **Today's date**: __TODAY__
- **Search window**: __START_DATE__ to __TODAY__ (recent 5 years)

## User Instructions

__USER_INSTRUCTIONS__

## Workflow

### Step 1: Understand the Project

Read the project's documentation and key source files:
- `README*`, `SECURITY*`, `CHANGELOG*`, release notes
- Build files (`Makefile`, `CMakeLists.txt`, `go.mod`, `Cargo.toml`, `package.json`, etc.)
- Top-level entry points and architecture

Determine:
- What the project does (protocol implementation, library, daemon, etc.)
- What language(s) it uses
- How it is deployed (standalone binary, library linked into other programs, network service, etc.)
- What attack surface it exposes (network listeners, file parsers, IPC, etc.)

### Step 2: Research Security History

Search for security-relevant information using a tiered approach:

1. **Project security policy**: Read `SECURITY.md` (or equivalent) to find the project's vulnerability disclosure process and, critically, any links to a **security announcements page** on the project's official website.

2. **Official security announcements**: If the project has a security advisory page (e.g., on its website, GitHub Security Advisories, or a dedicated mailing list mentioned in `SECURITY.md`), visit it and collect all CVEs and security fixes published in the window __START_DATE__ – __TODAY__.

3. **Git history**: Search commits for keywords: "CVE", "security", "fix", "vulnerability", "overflow", "injection", "bypass", "DOS", "crash", "patch" in the date range __START_DATE__ to __TODAY__. Pay attention to commits that fix bugs without explicitly using security language — these often indicate silently-patched vulnerabilities.

4. **Internet search (if needed)**: If the steps above yield few or no findings, search the internet for CVEs, security advisories, and vulnerability reports associated with this project. Check NVD, GitHub Advisory Database, and project-specific trackers.

For each finding, record: CVE ID (if any), affected component/function, vulnerability class, severity, and a one-line summary.

### Step 3: Identify Attacker Profile

Based on the project's purpose and deployment model, define the attacker:
- **Network attacker**: Can send arbitrary packets/messages to the service
- **Authenticated attacker**: Has valid credentials but attempts privilege escalation
- **Local attacker**: Has local access to the system running the software
- **Supply-chain attacker**: Targets the build/distribution process

Most network protocol implementations face a **network attacker** who can send malformed or malicious protocol messages.

### Step 4: Write Security Context Report

Write to **__OUTPUT_PATH__**. This document is for human review — it should be clear, well-organized, and useful as a standalone reference on this project's security landscape.

Use this structure:

```markdown
# Security Context

## Project Summary

- **Project**: {name}
- **Path**: __TARGET_PATH__
- **Language**: {primary language}
- **Description**: {2-4 sentences describing what the project does}
- **Deployment model**: {how the software is typically deployed}

## Attacker Profile

{Description of the primary attacker: capabilities, network position, goals. Note any secondary attacker models if relevant.}

## Attack Surface

{Enumerated list of attack surfaces: network listeners, protocol parsers, file handlers, IPC, crypto operations, etc. For each, briefly note what input it accepts and from whom.}

## Known Vulnerabilities and Security History

{Chronological list of CVEs, security advisories, and notable security-related commits found in Step 2. For each entry include: CVE ID (if any), date, affected component, vulnerability class, severity, and one-line description. If no findings, state that explicitly and note which sources were checked.}

## Vulnerability Patterns

{Analysis of recurring vulnerability patterns observed in the security history. What classes of bugs have historically been exploitable in this project? Which components are repeat offenders? What does this tell us about where new vulnerabilities are most likely to appear?}

## High-Value Vulnerability Classes

{Ranked list of the most impactful vulnerability types for this specific project, informed by its language, architecture, deployment model, and security history. For each, explain why it matters for this project:
1. {class} — {why it matters, what impact it enables}
2. {class} — {why, impact}
...}
```

### Step 5: Write Stage 5 Evaluation Guidance

Write distilled guidance to **__INSTRUCTION_STAGE5_PATH__**. Stage 5 sub-agents will read this file when evaluating individual bug reports from Stage 3. Each sub-agent must answer two questions: (1) Is this bug a security vulnerability? (2) If yes, how severe is it?

The guidance must help with **both** questions — distinguishing bugs from vulnerabilities is at least as important as severity scoring.

Include the following sections:

**Bug vs. Vulnerability Criteria** — Help the sub-agent decide whether a given bug crosses the line into a security vulnerability:
- What is the attacker profile? (from Step 3) What can the attacker control?
- A bug is a vulnerability only if an attacker can **reach** it through an attack surface and **exploit** it to violate a security property (confidentiality, integrity, availability, authentication, authorization).
- Reference the historical vulnerability list from Step 4: use past CVEs as concrete examples of what this project considers a security vulnerability. What bug classes have been assigned CVEs before? What components have had confirmed vulnerabilities? This calibrates the bar — if a similar bug in the same component was a CVE in the past, a new instance is likely a vulnerability too.
- Common reasons a bug is NOT a vulnerability: the code path is unreachable from attacker input; the bug is in dead/test/debug code; the impact is purely a logic error with no security consequence; existing mitigations (bounds checks, sandboxing, privilege separation) prevent exploitation.
- Project-specific guidance: based on this project's architecture and deployment, which kinds of bugs are most likely to be exploitable vs. benign?

**Severity Assessment** — Once a bug is confirmed as a vulnerability, guide severity scoring:
- The attacker profile and what they can achieve
- Historical severity benchmarks (what CVSS ranges have past CVEs for this project received?)
- Project-specific modifiers (e.g., "runs as root so crashes are High", "sandboxed by default so RCE is contained", "handles untrusted network input so parser bugs are directly reachable")
- The ranked vulnerability classes from Step 4
- Non-default configuration or compile-flag gating: if the vulnerable code path requires non-default settings, cap severity at Medium

## Completion Checklist

- [ ] Project documentation and source code surveyed
- [ ] Security announcements page visited (if available)
- [ ] Security history researched (git log, CVEs, advisories, internet search if needed)
- [ ] Attacker profile defined
- [ ] Security context report written to `__OUTPUT_PATH__` with all required sections
- [ ] Stage 5 evaluation guidance written to `__INSTRUCTION_STAGE5_PATH__` with both bug-vs-vulnerability criteria and severity assessment guidance
