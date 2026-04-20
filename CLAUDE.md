# CodeAuditor

Multi-stage code auditing agent using `claude-code-sdk` (Python). Given a target project, it researches security context → decomposes the codebase into analysis units → findings → vulnerabilities → PoC reproduction → disclosure preparation.

## Quick reference

- **Language**: Python >=3.12
- **Package manager**: pip (uses `pyproject.toml`, hatchling backend)
- **Entry point**: `code-auditor` CLI → `code_auditor/__main__.py:main`
- **Agent backend**: `claude-code-sdk` async `query()` API

## Running

```bash
# Install (editable)
pip install -e .

# Run an audit
code-auditor --target /path/to/project [--output-dir DIR] [--max-parallel 1] [--log-level DEBUG]

# Required args
#   --target                         Root directory of project to audit
# Optional args
#   --output-dir                     Defaults to {target}/audit-output
#   --max-parallel                   Concurrent agents (default 1)
#   --model                          Claude model to use (default claude-sonnet-4-6)
#   --target-au-count                Target number of analysis units for stage 3 (default 10)
#   --deployment-build-parallel      Max concurrent stage-2 build agents (default 1)
#   --deployment-build-timeout-sec   Wall-clock seconds per stage-2 build agent (default 1800)
#   --log-level                      DEBUG|INFO|WARNING|ERROR (default INFO)
```

## Testing

```bash
pytest                                    # run all tests
pytest code_auditor/tests/            # same thing
pytest -k test_stage2                     # filter by name
```

Tests are in `code_auditor/tests/test_parsers_and_report.py`. They cover parsers and validators — no agent calls needed.

## Project layout

```
code_auditor/
├── __main__.py          # CLI (argparse) → asyncio.run(run_audit)
├── config.py            # AuditConfig, Module, AnalysisUnit, ValidationIssue dataclasses
├── orchestrator.py      # Sequential stage runner
├── agent.py             # claude-code-sdk wrapper + validation retry loop
├── prompts.py           # load_prompt() with __KEY__ substitution
├── checkpoint.py        # File/marker-based checkpoint/resume
├── logger.py            # stdlib logging wrapper
├── utils.py             # run_parallel_limited, file helpers, severity sort
├── stages/              # stage0–stage7 (one file per stage)
├── parsing/             # stage2.py — extract structured data from agent output
├── validation/          # common.py + stage1–stage7 — validate agent output format
└── tests/
prompts/                 # stage1.md, stage2.md, stage2-build.md, stage3.md–stage7.md — prompt templates with __KEY__ placeholders
```

## Architecture (8 stages)

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

## Key patterns

- **Prompt templates**: `prompts/stageN.md` with `__KEY__` placeholders, loaded via `prompts.py:load_prompt()`
- **Directive injection**: Stage 1 produces auditing focus and vulnerability criteria directives; Stage 2 produces a deployment summary. Stage 3 receives auditing focus + vulnerability criteria + deployment summary; Stage 4 receives vulnerability criteria + deployment summary; Stage 6 receives the deployment summary (plus the deployment manifest path) to pick a pre-built deployment for PoC reproduction.
- **Validation + retry**: Each agent output is validated; on failure, a repair prompt is sent (up to `max_retries`)
- **Checkpoint/resume**: `.markers/` directory tracks completed sub-tasks; resume is automatic
- **Parallel agents**: `utils.run_parallel_limited()` uses `asyncio.Semaphore` + `gather`
- **Output dir layout**: `{output}/stage1-security-context/`, `stage2-deployments/`, `stage3-analysis-units/`, `stage4-findings/`, `stage5-vulnerabilities/`, `stage6-pocs/`, `stage7-disclosures/`, `.markers/`
