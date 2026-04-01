# Plan: Move Security Research to Stage 1

## Goal

Move the current Stage 4 (Security Context Research) to run as the **first agent stage** of the workflow (new Stage 1), so that all subsequent analysis stages benefit from project-specific security context. The research stage produces three files:

1. **Research record** (JSON) — structured record of all security research findings; serves as evidence base for generating directives and as an audit artifact
2. **Auditing focus directive** — identifies vulnerability-productive modules; injected into Stage 4 (bug discovery)
3. **Vulnerability criteria directive** — defines bug vs. vulnerability boundary; injected into Stage 4 (bug discovery) and Stage 5 (evaluation)

The directive files are stored separately so they can be **selectively injected** into downstream agents.

## Motivation

Currently, Stage 4 runs *after* bug discovery (Stage 3). This means Stage 3 agents hunt for bugs with no knowledge of the project's security history, attacker profile, or which vulnerability classes matter most. Moving research first lets every analysis agent benefit from:
- Historical vulnerability patterns (what bug classes have been CVEs before)
- Which modules and components are most vulnerability-productive
- A calibrated bar for what constitutes a vulnerability vs. a bug
- Project-specific scope declarations

## Current Stage Order

```
Stage 0: Setup (fs)
Stage 1: Decompose project → modules         (single agent)
Stage 2: Split modules → analysis units       (1 agent/module)
Stage 3: Bug discovery per AU                 (1 agent/AU)
Stage 4: Security context research            (single agent)
Stage 5: Evaluate findings                    (1 agent/finding)
Stage 6: Generate report                      (deterministic)
```

## New Stage Order

```
Stage 0: Setup (fs)
Stage 1: Security context research            (single agent)  ← was Stage 4
Stage 2: Decompose project → modules          (single agent)  ← was Stage 1
Stage 3: Split modules → analysis units       (1 agent/module) ← was Stage 2
Stage 4: Bug discovery per AU                 (1 agent/AU)    ← was Stage 3
Stage 5: Evaluate findings                    (1 agent/finding) (unchanged)
Stage 6: Generate report                      (deterministic)   (unchanged)
```

## Output Files from New Stage 1

### File A: Research Record

**Path**: `{output}/stage-1-security-context.json`

Structured JSON record of all research findings: project metadata, sources consulted, scope announcements, historical vulnerabilities, severity guidance, and fuzzing targets. This replaces the previous human-readable markdown report — the structured format makes it easier to generate directives from and to consume programmatically.

### File B: Auditing Focus Directive

**Path**: `{output}/stage-1-details/auditing-focus.md`

Identifies which modules, components, and code paths are most vulnerability-productive. Sections: explicit in/out-of-scope modules, historical hot spots.

**Injected into**: Stage 4 (bug discovery)

### File C: Vulnerability Criteria Directive

**Path**: `{output}/stage-1-details/vulnerability-criteria.md`

Defines the bug vs. vulnerability boundary with explicit scope declarations and historical calibration from past CVEs.

**Injected into**: Stage 4 (bug discovery) and Stage 5 (evaluation)

### Directive Injection Matrix

| Directive | Stage 4 (Bug Discovery) | Stage 5 (Evaluation) |
|---|---|---|
| Auditing Focus | ✓ | |
| Vulnerability Criteria | ✓ | ✓ |

## Research Sources (Tiered)

The research prompt uses a tiered source approach to avoid wasting agent time when early sources are sufficient:

1. **Tier 1 — Project docs**: SECURITY.md + follow links to project websites, security announcements, bug bounty programs
2. **Tier 2 — Git history + internet**: security-relevant commits, CVE searches, advisory databases
3. **Tier 3 — Deep sources (if sparse)**: fuzzing infrastructure, oss-security mailing list, NVD, OSV.dev, distro security trackers

## Changes Required

### 1. Rename and renumber stage files

| Current file | New file | Notes |
|---|---|---|
| `stages/stage1.py` | `stages/stage2.py` | Renumber, update task key to `"stage2"` |
| `stages/stage2.py` | `stages/stage3.py` | Renumber, update task key prefix |
| `stages/stage3.py` | `stages/stage4.py` | Renumber, update task key prefix |
| `stages/stage4.py` | `stages/stage1.py` | Renumber, update task key to `"stage1"`, update output paths |
| `stages/stage5.py` | (unchanged) | No renumber needed |
| `stages/stage6.py` | (unchanged) | No renumber needed |

Same renumbering for:
- `prompts/stage1.md` → `stage2.md`, etc.
- `validation/stage1.py` → `stage2.py`, etc.
- `parsing/stage1.py` → `stage2.py`, etc.

### 2. Update new Stage 1 (was Stage 4)

**`stages/stage1.py`** (the research stage):
- Change `_TASK_KEY` to `"stage1"`
- Update output paths: `stage-1-security-context.json` and `stage-1-details/{auditing-focus,vulnerability-criteria}.md`
- Update dataclass:

```python
@dataclass
class Stage1Output:
    research_record_path: str      # JSON research record
    auditing_focus_path: str       # directive for Stage 4
    vuln_criteria_path: str        # directive for Stage 4 + 5
```

- Update `load_prompt()` substitutions: `__OUTPUT_PATH__`, `__AUDITING_FOCUS_PATH__`, `__VULN_CRITERIA_PATH__`, `__TARGET_PATH__`, `__TODAY__`, `__START_DATE__`, `__USER_INSTRUCTIONS__`

**`prompts/stage1.md`** (the research prompt):
- New prompt (see `promt.md` in this plan directory)

**`validation/stage1.py`**: Validate that all three output files exist and are non-empty. Validate that the research record is valid JSON.

### 3. Update new Stage 4 (was Stage 3) — Bug Discovery

**`stages/stage4.py`**:
- Accept `auditing_focus_path: str` and `vuln_criteria_path: str` parameters
- Pass both to `load_prompt()` as new substitutions

**`prompts/stage4.md`** (was `stage3.md`):
- Add `__AUDITING_FOCUS_PATH__` and `__VULN_CRITERIA_PATH__` placeholders
- Add instruction at the top: "Before starting analysis, read the auditing focus at `__AUDITING_FOCUS_PATH__` and the vulnerability criteria at `__VULN_CRITERIA_PATH__`. The auditing focus tells you which components deserve the closest scrutiny. The vulnerability criteria define what distinguishes a vulnerability from a bug. Use this context to focus your analysis on reachable, exploitable issues."
- Keep the rest of the prompt unchanged

### 4. Update Stage 5 — Evaluation

**`stages/stage5.py`**:
- Accept `vuln_criteria_path: str` (replaces the single `instruction_path`)
- Pass to `load_prompt()` as new substitution

**`prompts/stage5.md`**:
- Replace `__INSTRUCTION_PATH__` with `__VULN_CRITERIA_PATH__`
- Update instruction: "Read the vulnerability criteria at `__VULN_CRITERIA_PATH__`."

### 5. Update orchestrator.py

```python
async def run_audit(config: AuditConfig) -> str:
    checkpoint = CheckpointManager(config.output_dir, config.resume)

    # Stage 0: setup
    if 0 not in config.skip_stages:
        await run_setup(config)

    # Stage 1: security context research (NEW POSITION)
    stage1_out: Stage1Output | None = None
    if 1 not in config.skip_stages:
        stage1_out = await run_stage1(config, checkpoint)

    # Resolve directive paths (from stage1 output or default locations)
    details_dir = os.path.join(config.output_dir, "stage-1-details")
    auditing_focus_path = (
        stage1_out.auditing_focus_path if stage1_out
        else os.path.join(details_dir, "auditing-focus.md")
    )
    vuln_criteria_path = (
        stage1_out.vuln_criteria_path if stage1_out
        else os.path.join(details_dir, "vulnerability-criteria.md")
    )

    # Stage 2: decompose project into modules (was Stage 1)
    modules: list[Module] = []
    if 2 not in config.skip_stages:
        modules = await run_stage2(config, checkpoint)
    else:
        logger.info("Stage 2 skipped.")
        modules = parse_modules(os.path.join(config.output_dir, "stage-2-modules.json"))

    # Stage 3: split modules into analysis units (was Stage 2)
    analysis_units: list[AnalysisUnit] = []
    if 3 not in config.skip_stages:
        analysis_units = await run_stage3(modules, config, checkpoint)
    else:
        # ... load from stage-3-details/

    # Stage 4: bug discovery per AU (was Stage 3)
    bug_files: list[str] = []
    if 4 not in config.skip_stages:
        bug_files = await run_stage4(
            analysis_units, config, checkpoint,
            auditing_focus_path, vuln_criteria_path,
        )
    else:
        # ... load from stage-4-details/

    # Stage 5: evaluate findings
    if 5 not in config.skip_stages:
        await run_stage5(bug_files, config, checkpoint, vuln_criteria_path)

    # Stage 6: generate report
    if 6 not in config.skip_stages:
        report_path = await run_stage6(config, checkpoint)
```

### 6. Update output directory layout

| Current | New |
|---|---|
| `stage-1-modules.json` | `stage-2-modules.json` |
| `stage-2-details/` | `stage-3-details/` |
| `stage-3-details/` | `stage-4-details/` |
| `stage-4-security-context.md` | `stage-1-security-context.json` |
| `stage-4-details/evaluation-guidance.md` | `stage-1-details/auditing-focus.md` |
| (new) | `stage-1-details/vulnerability-criteria.md` |
| `stage-5-details/` | (unchanged) |

### 7. Update Stage 0 (setup)

Update `run_setup()` to create the new directory names (`stage-1-details/`, `stage-3-details/`, `stage-4-details/`, `stage-5-details/`).

### 8. Update tests and parsing

- `parsing/stage1.py` → `parsing/stage2.py` (parses module JSON)
- `parsing/stage2.py` → `parsing/stage3.py` (parses AU JSON, if exists)
- Update test imports and references in `test_parsers_and_report.py`

### 9. Update CLAUDE.md

- Update the architecture table to reflect new stage numbering
- Update the project layout section
- Update CLI docs if `--skip-stages` examples reference old numbers

### 10. Update checkpoint compatibility

Old checkpoints use keys like `"stage1"`, `"stage3:AU-1"`, `"stage4"`. After renumbering, these won't match.
- **Simple**: Don't provide backward compatibility. Document that `--resume` won't work across the renumbering boundary. Users must re-run from scratch.
- This is acceptable since audits are typically run end-to-end.

## Implementation Order

1. Rename all stage/prompt/validation/parsing files to new numbers
2. Update all internal references (imports, task keys, output paths, directory names)
3. Update `stages/stage1.py` (research) — new dataclass with 3 output paths, new placeholder substitutions
4. Update `prompts/stage1.md` (research) — new prompt with tiered sources and 2 directives
5. Update `stages/stage4.py` (bug discovery) to accept `auditing_focus_path` and `vuln_criteria_path`
6. Update `prompts/stage4.md` (bug discovery) to read both directives
7. Update `stages/stage5.py` (evaluation) to accept `vuln_criteria_path`
8. Update `prompts/stage5.md` (evaluation) to read vulnerability criteria
9. Update `orchestrator.py` with new stage order, data flow, and selective injection
10. Update `stages/stage0.py` directory creation
11. Update tests
12. Update `CLAUDE.md`

## Risks

- **Renumbering churn**: Many files change names and internal references. Careful grep-and-replace needed.
- **Checkpoint incompatibility**: Old `--resume` won't work after renumbering. Acceptable tradeoff.
- **Context window budget**: Stage 4 agents receive two directives; Stage 5 agents receive one. Lightweight compared to the previous single-file approach.
- **Research quality without code context**: The research stage runs with access to the full codebase (it reads docs, source, git history). Moving it earlier doesn't change this — it still has the same access. No degradation expected.
