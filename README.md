# CodeAuditor

A multi-stage, agentic code auditing pipeline built on the [Claude Code SDK](https://github.com/anthropics/claude-code-sdk-python). Given a target source tree, CodeAuditor researches project context, decomposes the codebase into analysis units, hunts for bugs, evaluates them as security vulnerabilities, reproduces them with a working PoC, and finally prepares a disclosure-ready report package.

CodeAuditor has discovered several CVEs in widely used open-source projects — see [Vulnerabilities found](#vulnerabilities-found) below.

## How it works

The audit runs as eight sequential stages. Each stage is driven by a prompt template in `prompts/` and executed by one or more Claude Code agents. Outputs are validated, and on validation failure a repair prompt is sent (up to `max_retries`). Intermediate artifacts are written under the output directory; a `.markers/` folder tracks completed sub-tasks so runs can be resumed.

| Stage | What it does | Parallelism |
|-------|--------------|-------------|
| 0 | Git pull + create output directories | None |
| 1 | Security context research (git history, web, `SECURITY.md`) | Single agent |
| 2 | Deployment realization: research production deployments + build instrumented artifacts | Single research agent + N parallel build agents |
| 3 | Decompose the project into analysis units (AUs) | Single agent |
| 4 | Bug discovery per analysis unit | 1 agent per AU |
| 5 | Evaluate findings: real vulnerability? severity? | 1 agent per finding |
| 6 | PoC reproduction: launch a pre-built deployment + exploit + capture evidence | 1 agent per vulnerability |
| 7 | Disclosure: technical report, email, minimal PoC, zipped package | 1 agent per vulnerability |

Stage 1 produces two directives — an *auditing focus* and *vulnerability criteria* — that are injected into later stages so the whole pipeline stays aligned with the project's actual threat model.

## Requirements

- Python **3.12+**
- A working [Claude Code](https://docs.claude.com/en/docs/claude-code) install (the SDK reuses its authentication)
- Git, plus whatever build tools the target project needs for Stage 6 reproduction

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
| `--max-parallel` | Max concurrent agents (default: `1`). |
| `--model` | Claude model to use (default: `claude-sonnet-4-6`). |
| `--target-au-count` | Target number of analysis units for Stage 3 (default: `10`). |
| `--deployment-build-parallel` | Max concurrent stage-2 build agents (default: `1`). Separate from `--max-parallel` because builds are CPU/RAM heavy. |
| `--deployment-build-timeout-sec` | Wall-clock seconds per stage-2 build agent (default: `1800`). |
| `--log-level` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` (default: `INFO`). |

Runs resume from checkpoint markers automatically — delete the output directory (or its `.markers/` subdirectory) to start a fresh audit.

Existing audit outputs created before the deployment-realization stage was added are stage-numbered under the old scheme; they will not resume cleanly with the current code. Either finish them on the previous version or start fresh.

### Example

```bash
code-auditor \
  --target ~/projects/libfoo \
  --output-dir ~/audits/libfoo \
  --max-parallel 4 \
  --log-level DEBUG
```

## Output layout

```
{output-dir}/
├── stage1-security-context/    # context research + auditing focus + vuln criteria
├── stage2-deployments/         # deployment archetypes + per-config builds
├── stage3-analysis-units/      # codebase decomposition
├── stage4-findings/            # per-AU bug findings
├── stage5-vulnerabilities/     # evaluated, confirmed vulnerabilities
├── stage6-pocs/                # PoCs + evidence
├── stage7-disclosures/         # disclosure reports, emails, zipped PoCs
└── .markers/                   # checkpoint markers for resume
```

## Project layout

```
code_auditor/
├── __main__.py          # CLI entry point
├── config.py            # AuditConfig and dataclasses
├── orchestrator.py      # Sequential stage runner
├── agent.py             # claude-code-sdk wrapper + validation retry loop
├── prompts.py           # Prompt loader with __KEY__ substitution
├── checkpoint.py        # Marker-based checkpoint/resume
├── logger.py            # Logging helper
├── utils.py             # Parallelism + file helpers
├── stages/              # stage0 – stage7
├── parsing/             # Structured extraction from agent output
├── validation/          # Per-stage output validators
└── tests/
prompts/                 # stage1.md, stage2.md, stage2-build.md, stage3.md – stage7.md
```

## Development

```bash
pytest                       # run all tests
pytest code_auditor/tests    # same thing
pytest -k stage2             # filter by name
```

Tests cover parsers and validators; they do not make real agent calls.

## Vulnerabilities found

Vulnerabilities CodeAuditor has helped discover and disclose:

### [httpd](https://github.com/apache/httpd)
- CVE-2026-28780
- CVE-2026-34032

### [ImageMagick](https://github.com/ImageMagick/ImageMagick)
- CVE-2026-40312

### [libexif](https://github.com/libexif/libexif)
- CVE-2026-40385
- CVE-2026-40386

## Responsible use

CodeAuditor is intended for auditing code you own or have explicit permission to test, and for coordinated disclosure to upstream maintainers. Do not use it to target systems or projects without authorization.

## License

TBD.
