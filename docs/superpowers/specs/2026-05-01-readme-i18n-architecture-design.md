# Design: README Chinese i18n, Vulnerability Table, and ASCII Architecture

## Context
CodeAuditor currently has a single English `README.md`. The goal is to add a Chinese translation, improve the vulnerability section formatting, and add a visual system-design diagram.

## Language Selection
- **Approach:** Separate files with cross-linking badges.
- **Files:** `README.md` (English), `README.zh.md` (Chinese).
- **Badge style:** Shield-style markdown badges at the top of each file.
  - `README.md`: `🇺🇸 English | 中文`
  - `README.zh.md`: `English | 🇨🇳 中文`
- Clicking a badge jumps to the other file. This is the cleanest GitHub-native approach.

## Vulnerability Table
- **Location:** Replaces the current "Vulnerabilities found" nested list.
- **Format:** Single markdown table.
- **Columns (in order):** `CVE ID` | `Project` | `Year` | `Link`
- **Rows:** One row per CVE (not grouped by project).
- **Sorting:** By CVE ID ascending.

## ASCII Architecture Schema
- **Location:** New "System Design" subsection inside "How it works" (or immediately after it).
- **Format:** Unicode box-drawing characters (rounded corners, solid arrows).
- **Detail level:** High-level 7-stage pipeline only.
- **Content:**
  - Shows input (Target Source Tree) flowing into Stage 0.
  - Stages 0→1→2→3→4→5→6 in a horizontal pipeline.
  - Stage 1 emits two directives (auditing focus + vulnerability criteria) that feed forward into Stages 2, 3, and 4 (shown as dashed annotation lines).
  - Final output is the disclosure package.
- **Styling:** Each stage box is roughly 20 chars wide, aligned horizontally, with `──►` connectors.

## README.zh.md Content Strategy
- Complete, faithful translation of the entire English README.
- Preserves all markdown formatting, code blocks, table structures, and relative links.
- Project names, CVE IDs, CLI flags, and file paths remain in English (not translated).
- The architecture diagram stays as ASCII art (universal).

## Out of Scope
- No Mermaid diagrams (user explicitly requested ASCII).
- No auto-detection of browser language.
- No additional languages beyond English and Chinese.
