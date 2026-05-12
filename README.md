<p align="center">
  <b>🇺🇸 English</b> | <a href="README.zh.md">中文</a>
</p>

# CodeAuditor

A multi-stage, agentic code auditing pipeline that can run on the [Claude Code SDK](https://github.com/anthropics/claude-code-sdk-python) or the [Codex App Server Python SDK](https://github.com/openai/codex/blob/main/sdk/python/README.md). Given a target source tree, CodeAuditor researches project context, decomposes the codebase into analysis units, hunts for bugs, evaluates them as security vulnerabilities, reproduces them with a working PoC, and finally prepares a disclosure-ready report package.

CodeAuditor has discovered several CVEs in widely used open-source projects — see [Vulnerabilities found](#vulnerabilities-found) below.

## How it works

The audit runs as seven sequential stages. Each stage is driven by a prompt template in `prompts/` and executed by one or more backend agents. Outputs are validated, and on validation failure a repair prompt is sent (up to `max_retries`). Intermediate artifacts are written under the output directory; a `.markers/` folder tracks completed sub-tasks so runs can be resumed.

| Stage | What it does | Parallelism |
|-------|--------------|-------------|
| 0 | Git pull + create output directories | None |
| 1 | Security context research (git history, web, `SECURITY.md`) | Single agent |
| 2 | Decompose the project into analysis units (AUs) | Single agent |
| 3 | Bug discovery per analysis unit | 1 agent per AU |
| 4 | Evaluate findings: real vulnerability? severity? | 1 agent per finding |
| 5 | PoC reproduction: build, exploit, capture evidence | 1 agent per vulnerability |
| 6 | Disclosure: technical report, email, minimal PoC, zipped package | 1 agent per vulnerability |

Stage 1 produces two directives — an *auditing focus* and *vulnerability criteria* — that are injected into later stages so the whole pipeline stays aligned with the project's actual threat model.

### System Design

```
┌─────────────┐
│ Target Repo │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────────────────────┐
│  Stage 0    │     │      DIRECTIVE INJECTION    │
│    Init     │────►│  ┌─────────┐  ┌─────────┐  │
└─────────────┘     │  │Auditing │  │Vuln     │  │
       │            │  │ Focus   │  │Criteria │  │
       ▼            │  └───┬─────┘  └────┬────┘  │
┌─────────────┐     │      │             │       │
│  Stage 1    │────►│      └──────┬──────┘       │
│   Context   │     └─────────────┼──────────────┘
└─────────────┘                   │
       │                          │
       ▼                          ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Stage 2    │──►│  Stage 3    │──►│  Stage 4    │──►│  Stage 5    │──►│  Stage 6    │
│  Decompose  │   │   Discover  │   │   Evaluate  │   │     PoC     │   │   Disclose  │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └──────┬──────┘
                                                                                 │
                                                                                 ▼
                                                                          ┌─────────────┐
                                                                          │  Disclosure │
                                                                          │   Package   │
                                                                          └─────────────┘
```

## Requirements

- Python **3.12+**
- A working [Claude Code](https://docs.claude.com/en/docs/claude-code) install for `--backend claude` (the SDK reuses its authentication)
- A working Codex CLI at `/usr/local/bin/codex` with `codex app-server` support and local Codex auth/session for `--backend codex`
- Git, plus whatever build tools the target project needs for Stage 5 reproduction

## Installation

```bash
git clone https://github.com/<owner>/CodeAuditor.git
cd CodeAuditor
pip install -e .
```

This exposes the `code-auditor` CLI entry point.

## Usage

```bash
code-auditor --target /path/to/project [options]
```

### Common options

| Flag | Description |
|------|-------------|
| `--target` | **Required.** Root directory of the project to audit. |
| `--output-dir` | Output directory (default: `{target}/audit-output`). |
| `--discovered` | Reproduced bugs markdown file used by Stage 6 (default: `{target}/reproduced-bugs.md`). Pass a path to override where this cross-run record is read and updated. |
| `--wiki` | LLM wiki knowledge base directory. CodeAuditor treats it as read-only and gives agents stage-specific wiki search guidance. |
| `--max-parallel` | Max concurrent agents (default: `1`). |
| `--backend` | Agent backend: `claude` or `codex` (default: `claude`). |
| `--model` | Backend model override. Claude defaults to `claude-sonnet-4-6`; Codex uses the local Codex config default unless specified. |
| `--target-au-count` | Target number of analysis units for Stage 2 (default: `10`). |
| `--log-level` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` (default: `INFO`). |
| `--enable-timeout` | Enable per-stage agent timeouts. By default, CodeAuditor runs without per-stage agent timeouts for long-running targets such as QEMU. |

By default, Stage 6 creates or updates `{target}/reproduced-bugs.md`. Before generating disclosures, Stage 6 reads this file and skips reproduced bugs with matching dedupe metadata. After Stage 6 successfully writes disclosure output for a new reproduced bug, it appends a new entry to the same file. Use `--discovered /path/to/reproduced-bugs.md` to read and update a different markdown file.

### Wiki knowledge base

`--wiki /path/to/wiki` lets CodeAuditor use an existing LLM wiki knowledge base during the audit. CodeAuditor treats the wiki as read-only and instructs agents not to create, edit, or update wiki files. Enforce filesystem permissions externally if write prevention is required.

Recommended structure:

```text
wiki/
|-- index.md
|-- overview.md
|-- attack-surface.md
|-- auditing-guide.md
|-- exploit-patterns.md
|-- reproduction-workflow.md
|-- vulnerability-timeline.md
|-- entities/
|   `-- <component>.md
|-- concepts/
|   `-- <vulnerability-class>.md
`-- sources/
    `-- <cve-or-case-study>.md
```

`index.md` is recommended as the navigation entry point. Partial wikis are supported; stages skip absent files and use the pages that exist.

Runs resume from checkpoint markers automatically — delete the output directory (or its `.markers/` subdirectory) to start a fresh audit.

### Example

```bash
code-auditor \
  --target ~/projects/libfoo \
  --output-dir ~/audits/libfoo \
  --wiki ~/knowledge/libfoo-wiki \
  --max-parallel 4 \
  --log-level DEBUG
```

## Output layout

```
{output-dir}/
├── stage1-security-context/  # context research + auditing focus + vuln criteria
├── stage2-analysis-units/    # codebase decomposition
├── stage3-findings/          # per-AU bug findings
├── stage4-vulnerabilities/   # evaluated, confirmed vulnerabilities
├── stage5-pocs/              # PoCs + evidence
├── stage6-disclosures/       # disclosure reports, emails, zipped PoCs
└── .markers/          # checkpoint markers for --resume
```

Stage 6 also creates or updates `{target}/reproduced-bugs.md` by default. This target-root file is outside `{output-dir}` unless you point `--discovered` somewhere else.

## Project layout

```
code_auditor/
├── __main__.py          # CLI entry point
├── config.py            # AuditConfig and dataclasses
├── orchestrator.py      # Sequential stage runner
├── agent.py             # Backend wrappers + validation retry loop
├── prompts.py           # Prompt loader with __KEY__ substitution
├── checkpoint.py        # Marker-based checkpoint/resume
├── logger.py            # Logging helper
├── utils.py             # Parallelism + file helpers
├── stages/              # stage0 – stage6
├── parsing/             # Structured extraction from agent output
├── validation/          # Per-stage output validators
└── tests/
prompts/                 # stage1.md – stage6.md prompt templates
```

## Development

```bash
pytest                       # run all tests
pytest code_auditor/tests    # same thing
pytest -k stage2             # filter by name
```

Tests cover parsers and validators; they do not make real agent calls.

## Vulnerabilities Found

Vulnerabilities CodeAuditor has helped discover and disclose:

| CVE ID | Project | Year | Reference |
|--------|---------|------|-----------|
| CVE-2026-28780 | [httpd](https://github.com/apache/httpd) | 2026 | [GitHub](https://github.com/apache/httpd) |
| CVE-2026-34032 | [httpd](https://github.com/apache/httpd) | 2026 | [GitHub](https://github.com/apache/httpd) |
| CVE-2026-40312 | [ImageMagick](https://github.com/ImageMagick/ImageMagick) | 2026 | [GitHub](https://github.com/ImageMagick/ImageMagick) |
| CVE-2026-40385 | [libexif](https://github.com/libexif/libexif) | 2026 | [GitHub](https://github.com/libexif/libexif) |
| CVE-2026-40386 | [libexif](https://github.com/libexif/libexif) | 2026 | [GitHub](https://github.com/libexif/libexif) |
| CVE-2026-7180 | [QEMU](https://gitlab.com/qemu-project/qemu) | 2026 | [GitLab](https://gitlab.com/qemu-project/qemu) |
| CVE-2026-8341 | [QEMU](https://gitlab.com/qemu-project/qemu) | 2026 | [GitLab](https://gitlab.com/qemu-project/qemu) |
| CVE-2026-8348 | [QEMU](https://gitlab.com/qemu-project/qemu) | 2026 | [GitLab](https://gitlab.com/qemu-project/qemu) |
| Embargoed | [GStreamer](https://gitlab.freedesktop.org/gstreamer/gstreamer) | 2026 | [#5035](https://gitlab.freedesktop.org/gstreamer/gstreamer/-/work_items/5035) |
| Embargoed | [GStreamer](https://gitlab.freedesktop.org/gstreamer/gstreamer) | 2026 | [#5036](https://gitlab.freedesktop.org/gstreamer/gstreamer/-/work_items/5036) |
| Embargoed | [GStreamer](https://gitlab.freedesktop.org/gstreamer/gstreamer) | 2026 | [#5038](https://gitlab.freedesktop.org/gstreamer/gstreamer/-/work_items/5038) |
| Embargoed | [GStreamer](https://gitlab.freedesktop.org/gstreamer/gstreamer) | 2026 | [#5039](https://gitlab.freedesktop.org/gstreamer/gstreamer/-/work_items/5039) |

## Responsible use

CodeAuditor is intended for auditing code you own or have explicit permission to test, and for coordinated disclosure to upstream maintainers. Do not use it to target systems or projects without authorization.

**Important:** Before sending any vulnerability report to project maintainers, manually review the generated disclosure materials. Verify that the vulnerability is real, the severity assessment is accurate, and the proof-of-concept actually reproduces the issue. Automated findings may contain false positives or inaccuracies that could waste maintainers' time or damage your credibility.


## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

This software is provided for educational, research, and experimental purposes only. See the disclaimer at the top of the LICENSE file.
