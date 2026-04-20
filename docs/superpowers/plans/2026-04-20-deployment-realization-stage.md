# Deployment Realization Stage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Insert a new Stage 2 — *Deployment Realization* — between today's Stage 1 and Stage 2. The new stage researches how the target is deployed in production (Phase A) and builds instrumented per-archetype artifacts (Phase B). Downstream stages 3, 4, and 6 consume the resulting deployment summary; Stage 6 (PoC) launches a pre-built artifact instead of building ad-hoc.

**Architecture:** Two-phase stage. Phase A is a single research agent producing a manifest + per-archetype `deployment-mode.md`. Phase B fans out one build agent per archetype (parallel, capped by a new `--deployment-build-parallel` flag), each iterating until the build succeeds or it concludes infeasibility. A merge step folds per-config `result.json` outcomes into the final `manifest.json`. Existing stages 2–6 renumber to 3–7. The deployment summary is injected as an additive prompt placeholder into the renumbered stages 3, 4, and 6; stage 6 also gets a `Step 0` that selects a pre-built artifact and the existing LLM-based "Real-World Exploitability Assessment" step is dropped.

**Tech Stack:** Python 3.12+, `claude-code-sdk` async `query()`, `asyncio` (semaphore-bounded parallelism, `asyncio.wait` timeout), pytest, hatchling/`pyproject.toml`.

---

## Reference summary (file paths in current code, before renumber)

- Spec: `docs/superpowers/specs/2026-04-19-deployment-realization-stage-design.md`
- Stage runners: `code_auditor/stages/stage{0..6}.py`
- Validators: `code_auditor/validation/{common,stage1..stage6}.py`
- Parsers: `code_auditor/parsing/stage2.py`
- Prompt loader: `code_auditor/prompts.py` (`load_prompt(name, subs)` does `__KEY__` substitution)
- Agent wrapper: `code_auditor/agent.py` (`run_agent(prompt, config, cwd, allowed_tools, max_turns, model, effort, log_file)`)
- Parallelism helper: `code_auditor/utils.py:run_parallel_limited(items, concurrency, worker)`
- Checkpoint: `code_auditor/checkpoint.py:CheckpointManager` (hardcoded stage-key routing in `_resolve` / `_needs_marker`)
- Setup directories: `code_auditor/stages/stage0.py`
- CLI: `code_auditor/__main__.py`
- Config dataclass: `code_auditor/config.py:AuditConfig`
- Tests: `code_auditor/tests/test_parsers_and_report.py`

---

## Task 1: Baseline — confirm pytest passes before any changes

**Files:** none modified.

- [ ] **Step 1: Run full test suite from repo root**

Run: `cd /home/audit/code_auditor/CodeAuditor && pytest -q`
Expected: all tests pass (current baseline).

- [ ] **Step 2: Capture pytest summary in shell history for later comparison**

If any test fails on baseline, STOP and report — fixing baseline failures is out of scope for this plan.

---

## Task 2: Renumber pipeline stages 2→3, 3→4, 4→5, 5→6, 6→7

This is a single atomic refactor. All renames + content patches happen together; orchestrator and tests are updated in lockstep. After this task, pytest must pass again on the renumbered code with no behavior change.

**Files:**
- Rename: `code_auditor/stages/stage2.py` → `stage3.py`
- Rename: `code_auditor/stages/stage3.py` → `stage4.py`
- Rename: `code_auditor/stages/stage4.py` → `stage5.py`
- Rename: `code_auditor/stages/stage5.py` → `stage6.py`
- Rename: `code_auditor/stages/stage6.py` → `stage7.py`
- Rename: `code_auditor/validation/stage2.py` → `stage3.py`
- Rename: `code_auditor/validation/stage3.py` → `stage4.py`
- Rename: `code_auditor/validation/stage4.py` → `stage5.py`
- Rename: `code_auditor/validation/stage5.py` → `stage6.py`
- Rename: `code_auditor/validation/stage6.py` → `stage7.py`
- Rename: `code_auditor/parsing/stage2.py` → `parsing/stage3.py`
- Rename: `prompts/stage2.md` → `stage3.md`
- Rename: `prompts/stage3.md` → `stage4.md`
- Rename: `prompts/stage4.md` → `stage5.md`
- Rename: `prompts/stage5.md` → `stage6.md`
- Rename: `prompts/stage6.md` → `stage7.md`
- Modify: `code_auditor/orchestrator.py`
- Modify: `code_auditor/checkpoint.py`
- Modify: `code_auditor/stages/stage0.py`
- Modify: `code_auditor/tests/test_parsers_and_report.py`
- Modify: each renamed stage file (internal references)
- Modify: each renamed validation file (function name renames)
- Modify: each renamed prompt file (header `# Stage N` text and any other in-prompt stage-number references)

> **Tip:** rename FILES first with `git mv`, then patch contents, then run pytest. Do not interleave renames and content edits across the same file.

### 2.1 Rename files (do these in REVERSE order: stage6 → stage7 first, so you don't clobber)

- [ ] **Step 1: Rename stage runner files**

Run from repo root:
```bash
git mv code_auditor/stages/stage6.py code_auditor/stages/stage7.py
git mv code_auditor/stages/stage5.py code_auditor/stages/stage6.py
git mv code_auditor/stages/stage4.py code_auditor/stages/stage5.py
git mv code_auditor/stages/stage3.py code_auditor/stages/stage4.py
git mv code_auditor/stages/stage2.py code_auditor/stages/stage3.py
```

- [ ] **Step 2: Rename validation files**

```bash
git mv code_auditor/validation/stage6.py code_auditor/validation/stage7.py
git mv code_auditor/validation/stage5.py code_auditor/validation/stage6.py
git mv code_auditor/validation/stage4.py code_auditor/validation/stage5.py
git mv code_auditor/validation/stage3.py code_auditor/validation/stage4.py
git mv code_auditor/validation/stage2.py code_auditor/validation/stage3.py
```

- [ ] **Step 3: Rename parsing module**

```bash
git mv code_auditor/parsing/stage2.py code_auditor/parsing/stage3.py
```

- [ ] **Step 4: Rename prompts**

```bash
git mv prompts/stage6.md prompts/stage7.md
git mv prompts/stage5.md prompts/stage6.md
git mv prompts/stage4.md prompts/stage5.md
git mv prompts/stage3.md prompts/stage4.md
git mv prompts/stage2.md prompts/stage3.md
```

- [ ] **Step 5: Verify file layout**

Run: `ls code_auditor/stages/ code_auditor/validation/ code_auditor/parsing/ prompts/`

Expected — files present:
```
code_auditor/stages/: __init__.py stage0.py stage1.py stage3.py stage4.py stage5.py stage6.py stage7.py
code_auditor/validation/: __init__.py common.py stage1.py stage3.py stage4.py stage5.py stage6.py stage7.py
code_auditor/parsing/: stage3.py
prompts/: stage1.md stage3.md stage4.md stage5.md stage6.md stage7.md
```

There is intentionally NO `stage2.py` or `prompts/stage2.md` after this step — they will be created later for the new deployment realization stage.

### 2.2 Patch contents of renamed stage runner files

For each renamed stage runner, update: function name, `_TASK_KEY` / `_task_key` prefix, `get_logger("stageN")` name, `load_prompt("stageN.md", ...)` filename, output directory string (`stageN-…`), and any imports from renamed `validation`/`parsing` modules.

- [ ] **Step 6: Patch `code_auditor/stages/stage3.py` (was stage2 — AU decomposition)**

Replace the file's contents with:

```python
from __future__ import annotations

import os

from ..agent import run_agent
from ..checkpoint import CheckpointManager
from ..config import AnalysisUnit, AuditConfig
from ..logger import get_logger
from ..parsing.stage3 import parse_au_files, parse_auditing_focus
from ..prompts import load_prompt
from ..utils import format_validation_issues
from ..validation.stage3 import validate_stage3_dir

logger = get_logger("stage3")
_TASK_KEY = "stage3"


async def run_stage3(
    config: AuditConfig,
    checkpoint: CheckpointManager,
    auditing_focus_path: str,
) -> list[AnalysisUnit]:
    result_dir = os.path.join(config.output_dir, "stage3-analysis-units")
    os.makedirs(result_dir, exist_ok=True)
    log_file = os.path.join(result_dir, "agent.log")

    if checkpoint.is_complete(_TASK_KEY):
        logger.info("Stage 3 already complete, loading existing output.")
        return parse_au_files(result_dir)

    if config.resume and parse_au_files(result_dir):
        logger.info("Stage 3: Found existing intermediate results. Validating.")
        issues = validate_stage3_dir(result_dir, max_aus=config.target_au_count)
        if not issues:
            logger.info("Stage 3: Existing output is valid. Skipping agent re-run.")
            checkpoint.mark_complete(_TASK_KEY)
            units = parse_au_files(result_dir)
            logger.info("Stage 3 complete (restored). Analysis units: %s", ", ".join(u.id for u in units))
            return units
        logger.warning(
            "Stage 3: Existing output has validation issues:\n%s",
            format_validation_issues(issues),
        )
        logger.info("Stage 3: Running repair agent to fix validation issues.")
        repair_prompt = (
            f"The analysis unit files in `{result_dir}` failed validation. "
            "Please fix all issues listed below:\n\n"
            f"```\n{format_validation_issues(issues)}\n```"
        )
        await run_agent(repair_prompt, config, cwd=config.target, max_turns=10, log_file=log_file)
        issues = validate_stage3_dir(result_dir, max_aus=config.target_au_count)
        if not issues:
            checkpoint.mark_complete(_TASK_KEY)
            units = parse_au_files(result_dir)
            logger.info("Stage 3 complete (repaired). Analysis units: %s", ", ".join(u.id for u in units))
            return units
        logger.warning(
            "Stage 3: Repair failed, falling through to full re-run.\n%s",
            format_validation_issues(issues),
        )

    logger.info("Stage 3: Starting codebase decomposition (target AU count: %d).", config.target_au_count)

    scope_modules, hot_spots = parse_auditing_focus(auditing_focus_path)

    logger.info("Stage 3: Running agent to enumerate, triage, and create analysis units.")
    prompt = load_prompt("stage3.md", {
        "target_path": config.target,
        "result_dir": result_dir,
        "user_instructions": config.scope or "No additional scope constraints.",
        "scope_modules": scope_modules or "No scope information available.",
        "historical_hot_spots": hot_spots or "No historical data available.",
        "target_au_count": str(config.target_au_count),
    })

    await run_agent(prompt, config, cwd=config.target, max_turns=200, log_file=log_file)

    logger.info("Stage 3: Agent finished. Validating output.")
    issues = validate_stage3_dir(result_dir, max_aus=config.target_au_count)
    if issues:
        logger.warning(
            "Stage 3 validation issues:\n%s", format_validation_issues(issues),
        )
        logger.info("Stage 3: Running repair agent to fix validation issues.")
        repair_prompt = (
            f"The analysis unit files in `{result_dir}` failed validation. "
            "Please fix all issues listed below:\n\n"
            f"```\n{format_validation_issues(issues)}\n```"
        )
        await run_agent(repair_prompt, config, cwd=config.target, max_turns=10, log_file=log_file)

        issues = validate_stage3_dir(result_dir, max_aus=config.target_au_count)
        if issues:
            logger.warning(
                "Stage 3 validation still has issues after repair:\n%s",
                format_validation_issues(issues),
            )

    checkpoint.mark_complete(_TASK_KEY)
    units = parse_au_files(result_dir)
    logger.info("Stage 3 complete. Analysis units: %s", ", ".join(u.id for u in units))
    return units
```

(The Stage 3 deployment-summary placeholder argument will be added in Task 12 — leave the signature alone for now.)

- [ ] **Step 7: Patch `code_auditor/stages/stage4.py` (was stage3 — bug discovery)**

Replace contents with the following (function/key/logger/prompt-file/output-dir all updated; behavior unchanged):

```python
from __future__ import annotations

import os
import re

from ..agent import run_agent
from ..checkpoint import CheckpointManager
from ..config import AnalysisUnit, AuditConfig
from ..logger import get_logger
from ..prompts import load_prompt
from ..utils import format_validation_issues, list_matching_files, run_parallel_limited
from ..validation.stage4 import validate_stage4_file

logger = get_logger("stage4")


def _task_key(unit: AnalysisUnit) -> str:
    return f"stage4:{unit.id}"


async def _run_unit(
    unit: AnalysisUnit,
    config: AuditConfig,
    checkpoint: CheckpointManager,
    auditing_focus_path: str,
    vuln_criteria_path: str,
    unit_index: int = 0,
    total_units: int = 0,
) -> list[str]:
    key = _task_key(unit)
    result_dir = os.path.join(config.output_dir, "stage4-findings")
    log_file = os.path.join(result_dir, "logs", f"{unit.id}.log")
    escaped_id = re.escape(unit.id)
    finding_pattern = re.compile(rf"^{escaped_id}-F-\d+\.json$")
    progress = f"[{unit_index}/{total_units}]" if total_units else ""

    if checkpoint.is_complete(key):
        logger.info("Stage 4 %s: %s already complete, skipping.", progress, unit.id)
        return list_matching_files(result_dir, finding_pattern)

    logger.info("Stage 4 %s: Starting bug discovery for %s.", progress, unit.id)
    prompt = load_prompt("stage4.md", {
        "au_file_path": unit.au_file_path,
        "result_dir": result_dir,
        "finding_prefix": unit.id,
        "auditing_focus_path": auditing_focus_path,
        "vuln_criteria_path": vuln_criteria_path,
    })

    await run_agent(prompt, config, cwd=config.target, max_turns=200, log_file=log_file)

    logger.info("Stage 4 %s: Agent finished for %s. Validating findings.", progress, unit.id)
    finding_files = list_matching_files(result_dir, finding_pattern)
    for finding_file in finding_files:
        issues = validate_stage4_file(finding_file)
        if not issues:
            continue

        logger.warning("Stage 4: Validation failed for %s\n%s", finding_file, format_validation_issues(issues))
        repair_prompt = (
            f"The finding file at `{finding_file}` failed validation. "
            f"Please fix all issues listed below:\n\n```\n{format_validation_issues(issues)}\n```"
        )
        await run_agent(repair_prompt, config, cwd=config.target, max_turns=10, log_file=log_file)

        issues = validate_stage4_file(finding_file)
        if issues:
            logger.warning("Stage 4: Repair failed for %s\n%s", finding_file, format_validation_issues(issues))

    checkpoint.mark_complete(key)
    logger.info("Stage 4 %s: %s complete. Findings: %d", progress, unit.id, len(finding_files))
    return finding_files


async def run_stage4(
    units: list[AnalysisUnit],
    config: AuditConfig,
    checkpoint: CheckpointManager,
    auditing_focus_path: str,
    vuln_criteria_path: str,
) -> list[str]:
    if not units:
        logger.warning("Stage 4: No analysis units to process.")
        return []

    total = len(units)
    logger.info("Stage 4: Starting bug discovery across %d analysis units (max parallel: %d).", total, config.max_parallel)

    results = await run_parallel_limited(
        units,
        config.max_parallel,
        lambda unit, idx: _run_unit(
            unit, config, checkpoint, auditing_focus_path, vuln_criteria_path,
            unit_index=idx + 1, total_units=total,
        ),
    )

    all_finding_files: list[str] = []
    for i, (status, value, error) in enumerate(results):
        if i >= len(units):
            continue
        if status == "rejected":
            logger.error("Stage 4: %s failed: %s", units[i].id, error)
            continue
        if value:
            all_finding_files.extend(value)

    logger.info("Stage 4 complete. Total bug finding files: %s", len(all_finding_files))
    return all_finding_files
```

(The deployment-summary placeholder will be added in Task 13.)

- [ ] **Step 8: Patch `code_auditor/stages/stage5.py` (was stage4 — evaluation)**

Apply these substitutions throughout the file (use a single careful editor pass; the file is ~256 lines):

| Find | Replace |
|------|---------|
| `from ..validation.stage4 import validate_stage4_file` | `from ..validation.stage5 import validate_stage5_file` |
| `validate_stage4_file(` | `validate_stage5_file(` |
| `get_logger("stage4")` | `get_logger("stage5")` |
| `f"stage4:{` | `f"stage5:{` |
| `Stage 4` (inside log strings only — leave header comments referring to "stage 4 evaluator" if any) | `Stage 5` |
| `load_prompt("stage4.md"` | `load_prompt("stage5.md"` |
| `"stage3-findings"` | `"stage4-findings"` |
| `"stage4-vulnerabilities"` (all occurrences, including subpaths like `_pending` and `logs`) | `"stage5-vulnerabilities"` |
| `async def run_stage4(` | `async def run_stage5(` |

Verify `_task_key` body now reads `f"stage5:{finding_filename}"` and the `_backfill_stageN_markers` function name matches its log/comment context (rename internal helper `_backfill_stage4_markers` → `_backfill_stage5_markers` if you want consistency; not required for correctness).

- [ ] **Step 9: Patch `code_auditor/stages/stage6.py` (was stage5 — PoC)**

Substitutions throughout:

| Find | Replace |
|------|---------|
| `get_logger("stage5")` | `get_logger("stage6")` |
| `f"stage5:{vuln_id}"` | `f"stage6:{vuln_id}"` |
| `Stage 5` (in log strings/comments where it refers to *this* stage) | `Stage 6` |
| `load_prompt("stage5.md"` | `load_prompt("stage6.md"` |
| `"stage5-pocs"` | `"stage6-pocs"` |
| `async def run_stage5(` | `async def run_stage6(` |
| `async def _run_reproduce(` | (keep — internal helper) |

(The `Step 0` deployment selection wiring and `__DEPLOYMENT_MANIFEST_PATH__` substitution placeholder will be added in Task 14.)

- [ ] **Step 10: Patch `code_auditor/stages/stage7.py` (was stage6 — disclosure)**

Substitutions throughout:

| Find | Replace |
|------|---------|
| `get_logger("stage6")` | `get_logger("stage7")` |
| `f"stage6:{vuln_id}"` | `f"stage7:{vuln_id}"` |
| `Stage 6` (log strings/comments referring to *this* stage) | `Stage 7` |
| `load_prompt("stage6.md"` | `load_prompt("stage7.md"` |
| `"stage5-pocs"` (used to look up the PoC dir from the report path) | `"stage6-pocs"` |
| `"stage6-disclosures"` | `"stage7-disclosures"` |
| `"stage4-vulnerabilities"` (used in `_find_finding_file`) | `"stage5-vulnerabilities"` |
| `async def run_stage6(` | `async def run_stage7(` |
| `def _vuln_id_from_report(` body: docstring `stage5-pocs` | `stage6-pocs` |

### 2.3 Patch validation modules — rename functions and DEFAULT constants

Each renumbered validation module exports stage-numbered helpers that must shift in lockstep with the file rename.

- [ ] **Step 11: Patch `code_auditor/validation/stage3.py` (was stage2)**

Rename the functions exported from this file:

| Old name | New name |
|----------|----------|
| `validate_stage2_dir` | `validate_stage3_dir` |
| `validate_stage2_au_file` | `validate_stage3_au_file` |
| `validate_triage_file` | (unchanged — generic name) |

`DEFAULT_MAX_ANALYSIS_UNITS` keeps its name (no stage number).

Also update the docstring on `validate_stage3_dir` from `"Validate the directory of AU-*.json files and triage.json produced by stage 2."` to `"...produced by stage 3."`.

- [ ] **Step 12: Patch `code_auditor/validation/stage4.py` (was stage3)**

Rename `validate_stage3_file` → `validate_stage4_file`. Update internal docstrings/log strings referencing "stage 3" → "stage 4" where they describe *this* validator.

- [ ] **Step 13: Patch `code_auditor/validation/stage5.py` (was stage4)**

Rename `validate_stage4_file` → `validate_stage5_file`. Update docstrings.

- [ ] **Step 14: Patch `code_auditor/validation/stage6.py` (was stage5)**

Rename any `validate_stage5_*` exported function → `validate_stage6_*`. Update docstrings.

- [ ] **Step 15: Patch `code_auditor/validation/stage7.py` (was stage6)**

Rename any `validate_stage6_*` exported function → `validate_stage7_*`. Update docstrings.

### 2.4 Patch parsing module

- [ ] **Step 16: `code_auditor/parsing/stage3.py` (was parsing/stage2.py)** — content unchanged; the file's exported function names (`parse_au_files`, `parse_auditing_focus`) have no stage number. No edit required.

### 2.5 Patch prompt files (top-of-file headers + intra-prompt stage references)

Each renumbered prompt has a top header like `# Stage 2: …` and may reference its stage number in body text. Update each.

- [ ] **Step 17: `prompts/stage3.md`** — change `# Stage 2: Codebase Decomposition into Analysis Units` to `# Stage 3: Codebase Decomposition into Analysis Units`. Change "performing **Stage 2**" → "performing **Stage 3**".

- [ ] **Step 18: `prompts/stage4.md`** — change `# Stage 3: Vulnerability Analysis` to `# Stage 4: Vulnerability Analysis` and any in-body "Stage 3" references describing the stage's own role.

- [ ] **Step 19: `prompts/stage5.md`** — change `# Stage 4: Vulnerability Evaluation` to `# Stage 5: Vulnerability Evaluation` and inner references. (Note: the prompt also references "Stage 3" as the upstream stage producing finding input — update that to "Stage 4" since findings now come from renumbered stage 4.)

- [ ] **Step 20: `prompts/stage6.md`** — top header says PoC reproduction (no stage number in title — verify with `grep '^#' prompts/stage6.md`). Update any "Stage 5" references describing this stage's own role to "Stage 6".

- [ ] **Step 21: `prompts/stage7.md`** — top of file probably has a disclosure-themed header (likewise verify with `grep '^#' prompts/stage7.md`). Update any "Stage 6" references describing *this* stage to "Stage 7".

### 2.6 Patch checkpoint manager

- [ ] **Step 22: Update `code_auditor/checkpoint.py`**

Replace the `_resolve` and `_needs_marker` methods. Replace the entire class body content from `def is_complete` through end-of-class with:

```python
    def is_complete(self, task_key: str) -> bool:
        if not self._resume:
            return False
        resolved = self._resolve(task_key)
        if resolved is None:
            return False
        exists = os.path.exists(resolved)
        if exists:
            logger.debug("Checkpoint hit: %s -> %s", task_key, resolved)
        return exists

    def mark_complete(self, task_key: str) -> None:
        if not self._needs_marker(task_key):
            logger.debug("Checkpoint tracked by output file: %s", task_key)
            return
        os.makedirs(self._markers_dir, exist_ok=True)
        Path(self._marker_path(task_key)).touch()

    def _resolve(self, task_key: str) -> str | None:
        if task_key == "stage1":
            return os.path.join(self._output_dir, "stage1-security-context", "stage-1-security-context.json")
        if task_key == "stage2:research":
            return self._marker_path(task_key)
        if task_key.startswith("stage2:build:"):
            return self._marker_path(task_key)
        if task_key == "stage3":
            return self._marker_path(task_key)
        if task_key.startswith("stage4:"):
            return self._marker_path(task_key)
        if task_key.startswith("stage5:"):
            marker = self._marker_path(task_key)
            if os.path.exists(marker):
                return marker
            # Fall back to pending file for runs that predate marker-based tracking.
            filename = task_key[len("stage5:"):]
            return os.path.join(self._output_dir, "stage5-vulnerabilities", "_pending", filename)
        if task_key.startswith("stage6:"):
            return self._marker_path(task_key)
        if task_key.startswith("stage7:"):
            return self._marker_path(task_key)
        logger.warning("Unknown checkpoint task key: %s", task_key)
        return None

    def _needs_marker(self, task_key: str) -> bool:
        return (
            task_key == "stage2:research"
            or task_key.startswith("stage2:build:")
            or task_key == "stage3"
            or task_key.startswith("stage4:")
            or task_key.startswith("stage5:")
            or task_key.startswith("stage6:")
            or task_key.startswith("stage7:")
        )

    def _marker_path(self, task_key: str) -> str:
        return os.path.join(self._markers_dir, task_key.replace(":", "-"))
```

### 2.7 Patch stage 0 directory list

- [ ] **Step 23: Update `code_auditor/stages/stage0.py`** — replace the `directories` list inside `run_setup` with:

```python
    directories = [
        config.output_dir,
        os.path.join(config.output_dir, ".markers"),
        os.path.join(config.output_dir, "stage1-security-context"),
        os.path.join(config.output_dir, "stage2-deployments"),
        os.path.join(config.output_dir, "stage2-deployments", "configs"),
        os.path.join(config.output_dir, "stage3-analysis-units"),
        os.path.join(config.output_dir, "stage4-findings"),
        os.path.join(config.output_dir, "stage5-vulnerabilities"),
        os.path.join(config.output_dir, "stage5-vulnerabilities", "_pending"),
        os.path.join(config.output_dir, "stage6-pocs"),
        os.path.join(config.output_dir, "stage7-disclosures"),
    ]
```

### 2.8 Patch orchestrator

- [ ] **Step 24: Update `code_auditor/orchestrator.py`** — rename imports and call sites. Replace the file's contents with:

```python
from __future__ import annotations

import os

from .checkpoint import CheckpointManager
from .config import AnalysisUnit, AuditConfig
from .logger import get_logger
from .parsing.stage3 import parse_au_files
from .stages.stage0 import run_setup
from .stages.stage1 import Stage1Output, run_stage1
from .stages.stage3 import run_stage3
from .stages.stage4 import run_stage4
from .stages.stage5 import run_stage5
from .stages.stage6 import run_stage6
from .stages.stage7 import run_stage7
from .utils import list_json_files

logger = get_logger("orchestrator")


async def run_audit(config: AuditConfig) -> None:
    checkpoint = CheckpointManager(config.output_dir, config.resume)

    if config.resume:
        logger.info("Resume mode enabled. Existing output files and markers will be reused.")

    if 0 not in config.skip_stages:
        await run_setup(config)

    stage1_out: Stage1Output | None = None
    if 1 not in config.skip_stages:
        stage1_out = await run_stage1(config, checkpoint)

    details_dir = os.path.join(config.output_dir, "stage1-security-context")
    auditing_focus_path = (
        stage1_out.auditing_focus_path if stage1_out
        else os.path.join(details_dir, "auditing-focus.md")
    )
    vuln_criteria_path = (
        stage1_out.vuln_criteria_path if stage1_out
        else os.path.join(details_dir, "vulnerability-criteria.md")
    )

    # Stage 2 (deployment realization) is wired in Task 11.

    analysis_units: list[AnalysisUnit] = []
    if 3 not in config.skip_stages:
        analysis_units = await run_stage3(config, checkpoint, auditing_focus_path)
    else:
        logger.info("Stage 3 skipped. Loading existing analysis units.")
        stage3_dir = os.path.join(config.output_dir, "stage3-analysis-units")
        analysis_units = parse_au_files(stage3_dir)

    if not analysis_units and 4 not in config.skip_stages:
        raise RuntimeError("Stage 3 produced no analysis units.")

    bug_files: list[str] = []
    if 4 not in config.skip_stages:
        bug_files = await run_stage4(
            analysis_units, config, checkpoint,
            auditing_focus_path, vuln_criteria_path,
        )
    else:
        logger.info("Stage 4 skipped.")
        bug_files = list_json_files(os.path.join(config.output_dir, "stage4-findings"))

    vuln_files: list[str] = []
    if 5 not in config.skip_stages:
        vuln_files = await run_stage5(bug_files, config, checkpoint, vuln_criteria_path)
    else:
        logger.info("Stage 5 skipped.")
        stage5_dir = os.path.join(config.output_dir, "stage5-vulnerabilities")
        vuln_files = [f for f in list_json_files(stage5_dir) if "_pending" not in f]

    stage6_reports: list[str] = []
    if 6 not in config.skip_stages:
        stage6_reports = await run_stage6(vuln_files, config, checkpoint)
    else:
        logger.info("Stage 6 skipped. Loading existing reports.")
        stage6_dir = os.path.join(config.output_dir, "stage6-pocs")
        if os.path.isdir(stage6_dir):
            for name in sorted(os.listdir(stage6_dir)):
                entry = os.path.join(stage6_dir, name)
                if os.path.isdir(entry):
                    report = os.path.join(entry, "report.md")
                    if os.path.exists(report):
                        stage6_reports.append(report)

    if 7 not in config.skip_stages:
        await run_stage7(stage6_reports, config, checkpoint)
    else:
        logger.info("Stage 7 skipped.")

    logger.info("Audit complete.")
```

### 2.9 Patch tests

- [ ] **Step 25: Update `code_auditor/tests/test_parsers_and_report.py`**

Update the imports at the top of the file:

```python
from code_auditor.parsing.stage3 import parse_au_files, parse_auditing_focus
from code_auditor.validation.stage3 import (
    DEFAULT_MAX_ANALYSIS_UNITS,
    validate_stage3_au_file,
    validate_stage3_dir,
    validate_triage_file,
)
from code_auditor.validation.stage5 import validate_stage5_file
```

Then update every call site in the test file:
- `validate_stage2_au_file(` → `validate_stage3_au_file(`
- `validate_stage2_dir(` → `validate_stage3_dir(`
- `validate_stage4_file(` → `validate_stage5_file(`

Test function names stay as-is (e.g. `test_stage2_parser_reads_au_files`) — they describe historical context only and renaming them is cosmetic churn that risks breaking external `pytest -k` patterns.

### 2.10 Verify renumber

- [ ] **Step 26: Confirm no dangling references to old stage paths remain**

Run: `grep -rn 'stage2-analysis-units\|stage3-findings\|stage4-vulnerabilities\|stage5-pocs\|stage6-disclosures' code_auditor/ prompts/ 2>/dev/null`

Expected: no matches. (Use `grep` for this audit step — it's a one-shot verification across the rename, the bulk Edit tool can't do this kind of cross-file search.)

If matches are found, patch them.

- [ ] **Step 27: Confirm no dangling references to old prompt filenames in `load_prompt(...)` calls**

Run: `grep -rn 'load_prompt("stage2.md\|load_prompt("stage3.md\|load_prompt("stage4.md\|load_prompt("stage5.md\|load_prompt("stage6.md' code_auditor/ 2>/dev/null`

Expected: only `stage3.md`/`stage4.md`/`stage5.md`/`stage6.md`/`stage7.md` should appear, each at the corresponding renumbered stage runner. No `stage2.md` reference (the new Phase A prompt comes in Task 9).

- [ ] **Step 28: Run pytest**

Run: `pytest -q`
Expected: same green baseline as Task 1.

If anything fails, fix it before proceeding. Do NOT commit until pytest is green.

### 2.11 Commit the renumber

- [ ] **Step 29: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
renumber pipeline stages 2-6 to 3-7 to make room for new stage 2

Mechanical refactor: stages, validators, parsing, prompts, output
directory names, checkpoint keys, logger names, and tests all shifted
in lockstep. No behavior change. The new stage 2 (deployment
realization) is wired in subsequent commits.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Add `deployment_build_parallel` and `deployment_build_timeout_sec` config + CLI flag (TDD)

**Files:**
- Modify: `code_auditor/config.py`
- Modify: `code_auditor/__main__.py`
- Modify: `code_auditor/tests/test_parsers_and_report.py` (add CLI flag tests)

- [ ] **Step 1: Write failing test for the CLI flag default**

Append to `code_auditor/tests/test_parsers_and_report.py`:

```python
from code_auditor.__main__ import _build_parser  # add this import near the others
from code_auditor.config import AuditConfig


def test_cli_deployment_build_parallel_default_is_one():
    parser = _build_parser()
    args = parser.parse_args(["--target", "/tmp"])
    assert args.deployment_build_parallel == 1


def test_cli_deployment_build_parallel_can_be_overridden():
    parser = _build_parser()
    args = parser.parse_args(["--target", "/tmp", "--deployment-build-parallel", "4"])
    assert args.deployment_build_parallel == 4


def test_audit_config_has_deployment_build_fields():
    config = AuditConfig(target="/tmp", output_dir="/tmp/out")
    assert config.deployment_build_parallel == 1
    assert config.deployment_build_timeout_sec == 1800
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest -q -k 'deployment_build_parallel or deployment_build_fields'`
Expected: 3 FAILs (`AttributeError` on `args.deployment_build_parallel` and `AuditConfig.deployment_build_parallel`).

- [ ] **Step 3: Add the config fields**

Edit `code_auditor/config.py` — inside the `AuditConfig` dataclass, after `target_au_count: int = 10`, add:

```python
    deployment_build_parallel: int = 1
    deployment_build_timeout_sec: int = 1800   # 30-min wall-clock per build agent
```

- [ ] **Step 4: Add the CLI flag**

Edit `code_auditor/__main__.py`. In `_build_parser()`, after the `--target-au-count` argument, add:

```python
    parser.add_argument(
        "--deployment-build-parallel",
        type=int,
        default=1,
        help="Maximum concurrent deployment build agents in stage 2 (default: 1). "
             "Separate from --max-parallel because builds are CPU/RAM heavy.",
    )
    parser.add_argument(
        "--deployment-build-timeout-sec",
        type=int,
        default=1800,
        help="Wall-clock seconds per deployment build agent (default: 1800).",
    )
```

In `main()`, when constructing `AuditConfig`, add the two new fields:

```python
    config = AuditConfig(
        target=target,
        output_dir=output_dir,
        max_parallel=args.max_parallel,
        resume=True,
        log_level=args.log_level.upper(),
        model=args.model,
        target_au_count=args.target_au_count,
        deployment_build_parallel=args.deployment_build_parallel,
        deployment_build_timeout_sec=args.deployment_build_timeout_sec,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest -q -k 'deployment_build_parallel or deployment_build_fields'`
Expected: 3 PASS.

- [ ] **Step 6: Run full suite**

Run: `pytest -q`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add code_auditor/config.py code_auditor/__main__.py code_auditor/tests/test_parsers_and_report.py
git commit -m "$(cat <<'EOF'
add deployment_build_parallel + deployment_build_timeout_sec config

Separate parallelism knob for stage 2 build agents — distinct from
--max-parallel, which controls network-bound static-analysis agents.
Builds are CPU/RAM heavy; default is 1 to avoid stressing the host.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Add `code_auditor/validation/stage2.py` with three validators (TDD)

**Files:**
- Create: `code_auditor/validation/stage2.py`
- Modify: `code_auditor/tests/test_parsers_and_report.py` (add Phase A / Phase B / final-manifest test cases)

The three validator signatures, per spec:
- `validate_stage2_phase_a(deployments_dir: str) -> list[ValidationIssue]`
- `validate_stage2_phase_b_entry(config_dir: str) -> list[ValidationIssue]`
- `validate_stage2_manifest_final(manifest_path: str) -> list[ValidationIssue]`

### 4.1 Phase A validator — TDD

- [ ] **Step 1: Write failing test for Phase A happy path**

Append to test file:

```python
from code_auditor.validation.stage2 import (
    validate_stage2_phase_a,
    validate_stage2_phase_b_entry,
    validate_stage2_manifest_final,
)


def _make_phase_a_layout(tmp: str, configs: list[dict]) -> None:
    """Create a deployments_dir layout matching what Phase A would produce."""
    os.makedirs(os.path.join(tmp, "configs"), exist_ok=True)
    with open(os.path.join(tmp, "deployment-summary.md"), "w") as f:
        f.write("# Deployment Summary\n\nA non-empty summary.\n")
    for cfg in configs:
        cfg_dir = os.path.join(tmp, "configs", cfg["id"])
        os.makedirs(cfg_dir, exist_ok=True)
        with open(os.path.join(cfg_dir, "deployment-mode.md"), "w") as f:
            f.write(f"# {cfg['name']}\n\nNon-empty deployment-mode body.\n")
    manifest = {"configs": configs}
    with open(os.path.join(tmp, "manifest.json"), "w") as f:
        json.dump(manifest, f)


def _phase_a_config(cfg_id: str = "httpd-static-tls") -> dict:
    return {
        "id": cfg_id,
        "name": "Static web server with TLS",
        "deployment_mode_path": f"configs/{cfg_id}/deployment-mode.md",
        "exposed_surface": ["http parser", "tls handshake"],
        "modules_exercised": ["server/", "modules/ssl/"],
        "build_status": None,
        "artifact_path": None,
        "launch_cmd": None,
        "build_failure_reason": None,
        "attempts_summary": None,
    }


def test_validate_stage2_phase_a_accepts_valid_layout():
    with tempfile.TemporaryDirectory() as tmp:
        _make_phase_a_layout(tmp, [_phase_a_config()])
        assert validate_stage2_phase_a(tmp) == []


def test_validate_stage2_phase_a_rejects_missing_manifest():
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "deployment-summary.md"), "w") as f:
            f.write("x\n")
        issues = validate_stage2_phase_a(tmp)
        assert any("manifest.json" in i.description for i in issues)


def test_validate_stage2_phase_a_rejects_empty_configs():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "configs"), exist_ok=True)
        with open(os.path.join(tmp, "deployment-summary.md"), "w") as f:
            f.write("x\n")
        with open(os.path.join(tmp, "manifest.json"), "w") as f:
            json.dump({"configs": []}, f)
        issues = validate_stage2_phase_a(tmp)
        assert any("at least one" in i.description.lower() for i in issues)


def test_validate_stage2_phase_a_rejects_non_kebab_id():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _phase_a_config("HttpdStaticTLS")  # camel/pascal case, not kebab
        cfg["deployment_mode_path"] = "configs/HttpdStaticTLS/deployment-mode.md"
        _make_phase_a_layout(tmp, [cfg])
        issues = validate_stage2_phase_a(tmp)
        assert any("kebab" in i.description.lower() for i in issues)


def test_validate_stage2_phase_a_rejects_duplicate_ids():
    with tempfile.TemporaryDirectory() as tmp:
        a = _phase_a_config("dup")
        b = _phase_a_config("dup")
        _make_phase_a_layout(tmp, [a, b])
        issues = validate_stage2_phase_a(tmp)
        assert any("duplicate" in i.description.lower() for i in issues)


def test_validate_stage2_phase_a_rejects_empty_exposed_surface():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _phase_a_config()
        cfg["exposed_surface"] = []
        _make_phase_a_layout(tmp, [cfg])
        issues = validate_stage2_phase_a(tmp)
        assert any("exposed_surface" in i.description for i in issues)


def test_validate_stage2_phase_a_rejects_empty_modules_exercised():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _phase_a_config()
        cfg["modules_exercised"] = []
        _make_phase_a_layout(tmp, [cfg])
        issues = validate_stage2_phase_a(tmp)
        assert any("modules_exercised" in i.description for i in issues)


def test_validate_stage2_phase_a_rejects_missing_deployment_mode_file():
    with tempfile.TemporaryDirectory() as tmp:
        _make_phase_a_layout(tmp, [_phase_a_config()])
        os.remove(os.path.join(tmp, "configs", "httpd-static-tls", "deployment-mode.md"))
        issues = validate_stage2_phase_a(tmp)
        assert any("deployment-mode.md" in i.description for i in issues)


def test_validate_stage2_phase_a_rejects_empty_deployment_mode_file():
    with tempfile.TemporaryDirectory() as tmp:
        _make_phase_a_layout(tmp, [_phase_a_config()])
        with open(os.path.join(tmp, "configs", "httpd-static-tls", "deployment-mode.md"), "w") as f:
            f.write("")
        issues = validate_stage2_phase_a(tmp)
        assert any("deployment-mode.md" in i.description and "empty" in i.description.lower() for i in issues)


def test_validate_stage2_phase_a_rejects_missing_summary():
    with tempfile.TemporaryDirectory() as tmp:
        _make_phase_a_layout(tmp, [_phase_a_config()])
        os.remove(os.path.join(tmp, "deployment-summary.md"))
        issues = validate_stage2_phase_a(tmp)
        assert any("deployment-summary.md" in i.description for i in issues)


def test_validate_stage2_phase_a_rejects_prematurely_set_build_fields():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _phase_a_config()
        cfg["build_status"] = "ok"
        _make_phase_a_layout(tmp, [cfg])
        issues = validate_stage2_phase_a(tmp)
        assert any("build_status" in i.description and "null" in i.description.lower() for i in issues)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest -q -k 'validate_stage2_phase_a'`
Expected: ~11 FAILs (`ImportError: cannot import name 'validate_stage2_phase_a'`).

- [ ] **Step 3: Create `code_auditor/validation/stage2.py` with the Phase A validator**

```python
from __future__ import annotations

import json
import os
import re
from typing import Any

from ..config import ValidationIssue

_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_VACUOUS_REASONS = {"build failed", "unknown error", "failed", "error"}
_VALID_BUILD_STATUSES = {"ok", "infeasible", "timeout"}
_PHASE_A_BUILD_FIELDS = (
    "build_status",
    "artifact_path",
    "launch_cmd",
    "build_failure_reason",
    "attempts_summary",
)


def _issue(description: str, expected: str, fix: str) -> ValidationIssue:
    return ValidationIssue(description=description, expected=expected, fix=fix)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_nonempty_list_of_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(isinstance(x, str) and x.strip() for x in value)
    )


def _read_json(path: str) -> tuple[Any, list[ValidationIssue]]:
    if not os.path.exists(path):
        return None, [_issue(
            description=f"File not found: {path}",
            expected="The file should exist.",
            fix="Ensure the file is written before validation.",
        )]
    try:
        with open(path) as f:
            return json.load(f), []
    except json.JSONDecodeError as e:
        return None, [_issue(
            description=f"{os.path.basename(path)}: invalid JSON: {e}",
            expected="Valid JSON.",
            fix="Fix the JSON syntax error.",
        )]


def validate_stage2_phase_a(deployments_dir: str) -> list[ValidationIssue]:
    """Validate the layout produced by Phase A (research) before Phase B runs."""
    issues: list[ValidationIssue] = []

    if not os.path.isdir(deployments_dir):
        return [_issue(
            description=f"Deployments directory does not exist: {deployments_dir}",
            expected="A directory containing manifest.json, deployment-summary.md, and configs/.",
            fix="Run the Phase A research agent.",
        )]

    summary_path = os.path.join(deployments_dir, "deployment-summary.md")
    if not os.path.exists(summary_path) or os.path.getsize(summary_path) == 0:
        issues.append(_issue(
            description="deployment-summary.md is missing or empty.",
            expected="A non-empty summary file at deployment-summary.md.",
            fix="Write deployment-summary.md with one paragraph per archetype.",
        ))

    manifest_path = os.path.join(deployments_dir, "manifest.json")
    data, read_issues = _read_json(manifest_path)
    issues.extend(read_issues)
    if data is None:
        return issues

    if not isinstance(data, dict) or "configs" not in data:
        issues.append(_issue(
            description="manifest.json: missing top-level 'configs' array.",
            expected="A JSON object with a 'configs' array.",
            fix="Wrap the entries in {\"configs\": [...]}.",
        ))
        return issues

    configs = data["configs"]
    if not isinstance(configs, list):
        issues.append(_issue(
            description="manifest.json: 'configs' is not a list.",
            expected="A JSON array.",
            fix="Make 'configs' a JSON array.",
        ))
        return issues

    if len(configs) == 0:
        issues.append(_issue(
            description="manifest.json: 'configs' must contain at least one archetype.",
            expected="At least one deployment archetype.",
            fix="Add at least one archetype to 'configs'.",
        ))
        return issues

    seen_ids: set[str] = set()
    for i, entry in enumerate(configs):
        if not isinstance(entry, dict):
            issues.append(_issue(
                description=f"manifest.json[{i}]: entry is not an object.",
                expected="Each entry must be a JSON object.",
                fix=f"Fix entry at index {i}.",
            ))
            continue

        cfg_id = entry.get("id")
        if not _is_nonempty_string(cfg_id):
            issues.append(_issue(
                description=f"manifest.json[{i}]: missing or blank 'id'.",
                expected="A non-empty kebab-case id.",
                fix=f"Add an 'id' to entry {i}.",
            ))
            continue

        if not _KEBAB_RE.match(cfg_id):
            issues.append(_issue(
                description=f"manifest.json[{i}]: id '{cfg_id}' is not kebab-case.",
                expected="kebab-case (lowercase letters, digits, hyphens).",
                fix=f"Rename '{cfg_id}' to kebab-case.",
            ))

        if cfg_id in seen_ids:
            issues.append(_issue(
                description=f"manifest.json[{i}]: duplicate id '{cfg_id}'.",
                expected="Unique ids across the manifest.",
                fix=f"Pick a different id for one of the duplicates.",
            ))
        seen_ids.add(cfg_id)

        if not _is_nonempty_string(entry.get("name")):
            issues.append(_issue(
                description=f"manifest.json[{cfg_id}]: missing or blank 'name'.",
                expected="A short human-readable name.",
                fix="Add a 'name'.",
            ))

        if not _is_nonempty_list_of_strings(entry.get("exposed_surface")):
            issues.append(_issue(
                description=f"manifest.json[{cfg_id}]: 'exposed_surface' must be a non-empty list of strings.",
                expected="Non-empty list of strings.",
                fix="Add at least one exposed-surface entry.",
            ))

        if not _is_nonempty_list_of_strings(entry.get("modules_exercised")):
            issues.append(_issue(
                description=f"manifest.json[{cfg_id}]: 'modules_exercised' must be a non-empty list of strings.",
                expected="Non-empty list of strings.",
                fix="Add at least one module path.",
            ))

        dm_path_rel = entry.get("deployment_mode_path")
        if not _is_nonempty_string(dm_path_rel):
            issues.append(_issue(
                description=f"manifest.json[{cfg_id}]: missing or blank 'deployment_mode_path'.",
                expected="A path relative to the deployments dir.",
                fix=f"Set 'deployment_mode_path' to configs/{cfg_id}/deployment-mode.md",
            ))
        else:
            dm_path = os.path.join(deployments_dir, dm_path_rel)
            if not os.path.exists(dm_path):
                issues.append(_issue(
                    description=f"{cfg_id}: deployment-mode.md does not exist at {dm_path_rel}.",
                    expected="A non-empty deployment-mode.md file.",
                    fix=f"Write deployment-mode.md for {cfg_id}.",
                ))
            elif os.path.getsize(dm_path) == 0:
                issues.append(_issue(
                    description=f"{cfg_id}: deployment-mode.md is empty at {dm_path_rel}.",
                    expected="A non-empty file describing the deployment mode.",
                    fix=f"Write a deployment-mode body for {cfg_id}.",
                ))

        for build_field in _PHASE_A_BUILD_FIELDS:
            if entry.get(build_field) is not None:
                issues.append(_issue(
                    description=f"manifest.json[{cfg_id}]: '{build_field}' must be null after Phase A.",
                    expected=f"'{build_field}' is null until Phase B runs.",
                    fix=f"Remove the '{build_field}' value or set it to null.",
                ))

    return issues
```

- [ ] **Step 4: Run Phase A tests to verify they pass**

Run: `pytest -q -k 'validate_stage2_phase_a'`
Expected: 11 PASS.

### 4.2 Phase B entry validator — TDD

- [ ] **Step 5: Write failing tests for Phase B entry validator**

Append:

```python
def _make_phase_b_layout(cfg_dir: str, result: dict, scripts: bool = True, artifact: bool = True) -> None:
    os.makedirs(cfg_dir, exist_ok=True)
    with open(os.path.join(cfg_dir, "result.json"), "w") as f:
        json.dump(result, f)
    if scripts:
        for name in ("build.sh", "launch.sh", "smoke-test.sh"):
            path = os.path.join(cfg_dir, name)
            with open(path, "w") as f:
                f.write("#!/bin/sh\n")
            os.chmod(path, 0o755)
    if artifact and result.get("artifact_path"):
        artifact_path = result["artifact_path"]
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        with open(artifact_path, "w") as f:
            f.write("binary")


def test_validate_stage2_phase_b_entry_accepts_ok():
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = os.path.join(tmp, "configs", "httpd-static-tls")
        artifact = os.path.join(cfg_dir, "build", "httpd")
        _make_phase_b_layout(cfg_dir, {
            "id": "httpd-static-tls",
            "build_status": "ok",
            "artifact_path": artifact,
            "launch_cmd": f"{cfg_dir}/launch.sh",
            "build_failure_reason": None,
            "attempts_summary": None,
        })
        assert validate_stage2_phase_b_entry(cfg_dir) == []


def test_validate_stage2_phase_b_entry_accepts_infeasible():
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = os.path.join(tmp, "configs", "exotic")
        _make_phase_b_layout(cfg_dir, {
            "id": "exotic",
            "build_status": "infeasible",
            "artifact_path": None,
            "launch_cmd": None,
            "build_failure_reason": "requires RDMA hardware not present in this environment",
            "attempts_summary": "tried installing libibverbs; kernel module missing.",
        }, scripts=False, artifact=False)
        assert validate_stage2_phase_b_entry(cfg_dir) == []


def test_validate_stage2_phase_b_entry_rejects_id_mismatch():
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = os.path.join(tmp, "configs", "expected-id")
        artifact = os.path.join(cfg_dir, "build", "x")
        _make_phase_b_layout(cfg_dir, {
            "id": "different-id",
            "build_status": "ok",
            "artifact_path": artifact,
            "launch_cmd": "x",
            "build_failure_reason": None,
            "attempts_summary": None,
        })
        issues = validate_stage2_phase_b_entry(cfg_dir)
        assert any("id" in i.description and "match" in i.description for i in issues)


def test_validate_stage2_phase_b_entry_rejects_unknown_status():
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = os.path.join(tmp, "configs", "x")
        _make_phase_b_layout(cfg_dir, {
            "id": "x",
            "build_status": "weird",
            "artifact_path": None,
            "launch_cmd": None,
            "build_failure_reason": None,
            "attempts_summary": None,
        }, scripts=False, artifact=False)
        issues = validate_stage2_phase_b_entry(cfg_dir)
        assert any("build_status" in i.description for i in issues)


def test_validate_stage2_phase_b_entry_ok_requires_artifact_on_disk():
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = os.path.join(tmp, "configs", "x")
        _make_phase_b_layout(cfg_dir, {
            "id": "x",
            "build_status": "ok",
            "artifact_path": "/nonexistent/path/binary",
            "launch_cmd": "x",
            "build_failure_reason": None,
            "attempts_summary": None,
        }, artifact=False)
        issues = validate_stage2_phase_b_entry(cfg_dir)
        assert any("artifact_path" in i.description for i in issues)


def test_validate_stage2_phase_b_entry_ok_requires_executable_scripts():
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = os.path.join(tmp, "configs", "x")
        artifact = os.path.join(cfg_dir, "build", "x")
        _make_phase_b_layout(cfg_dir, {
            "id": "x",
            "build_status": "ok",
            "artifact_path": artifact,
            "launch_cmd": "x",
            "build_failure_reason": None,
            "attempts_summary": None,
        })
        # Strip exec bit on launch.sh
        os.chmod(os.path.join(cfg_dir, "launch.sh"), 0o644)
        issues = validate_stage2_phase_b_entry(cfg_dir)
        assert any("launch.sh" in i.description and "executable" in i.description for i in issues)


def test_validate_stage2_phase_b_entry_infeasible_rejects_vacuous_reason():
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = os.path.join(tmp, "configs", "x")
        _make_phase_b_layout(cfg_dir, {
            "id": "x",
            "build_status": "infeasible",
            "artifact_path": None,
            "launch_cmd": None,
            "build_failure_reason": "build failed",
            "attempts_summary": "tried.",
        }, scripts=False, artifact=False)
        issues = validate_stage2_phase_b_entry(cfg_dir)
        assert any("build_failure_reason" in i.description and "vacuous" in i.description.lower() for i in issues)


def test_validate_stage2_phase_b_entry_infeasible_requires_attempts_summary():
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = os.path.join(tmp, "configs", "x")
        _make_phase_b_layout(cfg_dir, {
            "id": "x",
            "build_status": "infeasible",
            "artifact_path": None,
            "launch_cmd": None,
            "build_failure_reason": "missing libfoo, no apt package available",
            "attempts_summary": "",
        }, scripts=False, artifact=False)
        issues = validate_stage2_phase_b_entry(cfg_dir)
        assert any("attempts_summary" in i.description for i in issues)


def test_validate_stage2_phase_b_entry_missing_result_json():
    with tempfile.TemporaryDirectory() as tmp:
        cfg_dir = os.path.join(tmp, "configs", "x")
        os.makedirs(cfg_dir, exist_ok=True)
        issues = validate_stage2_phase_b_entry(cfg_dir)
        assert any("result.json" in i.description for i in issues)
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `pytest -q -k 'validate_stage2_phase_b'`
Expected: 9 FAILs (`ImportError`).

- [ ] **Step 7: Implement `validate_stage2_phase_b_entry` in `code_auditor/validation/stage2.py`**

Append to the file:

```python
def validate_stage2_phase_b_entry(config_dir: str) -> list[ValidationIssue]:
    """Validate the per-config result.json + script artifacts produced by a Phase B agent."""
    issues: list[ValidationIssue] = []

    expected_id = os.path.basename(os.path.normpath(config_dir))
    result_path = os.path.join(config_dir, "result.json")

    data, read_issues = _read_json(result_path)
    issues.extend(read_issues)
    if data is None:
        return issues

    if not isinstance(data, dict):
        return issues + [_issue(
            description=f"{expected_id}/result.json: top-level value is not an object.",
            expected="A JSON object.",
            fix="Wrap the contents in {...}.",
        )]

    actual_id = data.get("id")
    if actual_id != expected_id:
        issues.append(_issue(
            description=f"{expected_id}/result.json: 'id' ({actual_id!r}) does not match config dir name.",
            expected=f"id == {expected_id!r}",
            fix=f"Set 'id' to '{expected_id}' in result.json.",
        ))

    status = data.get("build_status")
    if status not in _VALID_BUILD_STATUSES:
        issues.append(_issue(
            description=f"{expected_id}/result.json: 'build_status' must be one of {sorted(_VALID_BUILD_STATUSES)}, got {status!r}.",
            expected=f"build_status ∈ {sorted(_VALID_BUILD_STATUSES)}",
            fix="Set build_status to one of the allowed values.",
        ))
        return issues  # downstream checks depend on a valid status

    if status == "ok":
        artifact_path = data.get("artifact_path")
        launch_cmd = data.get("launch_cmd")
        if not _is_nonempty_string(artifact_path):
            issues.append(_issue(
                description=f"{expected_id}/result.json: 'artifact_path' must be a non-empty string when build_status == 'ok'.",
                expected="A path to the launchable artifact.",
                fix="Set artifact_path to the built artifact path.",
            ))
        elif not os.path.exists(artifact_path):
            issues.append(_issue(
                description=f"{expected_id}/result.json: 'artifact_path' does not exist on disk: {artifact_path}.",
                expected="An existing artifact path.",
                fix="Verify the build produced the artifact at this path.",
            ))
        if not _is_nonempty_string(launch_cmd):
            issues.append(_issue(
                description=f"{expected_id}/result.json: 'launch_cmd' must be a non-empty string when build_status == 'ok'.",
                expected="A shell command (or path to launch.sh).",
                fix="Set launch_cmd.",
            ))

        for script in ("build.sh", "launch.sh", "smoke-test.sh"):
            script_path = os.path.join(config_dir, script)
            if not os.path.exists(script_path):
                issues.append(_issue(
                    description=f"{expected_id}: required script {script} is missing.",
                    expected=f"{script} exists in the config directory.",
                    fix=f"Author {script} as part of the build agent's work.",
                ))
                continue
            if not os.access(script_path, os.X_OK):
                issues.append(_issue(
                    description=f"{expected_id}: {script} is not executable.",
                    expected=f"{script} has the executable bit set.",
                    fix=f"chmod +x {script_path}",
                ))

    else:  # infeasible or timeout
        reason = data.get("build_failure_reason")
        if not _is_nonempty_string(reason):
            issues.append(_issue(
                description=f"{expected_id}/result.json: 'build_failure_reason' is required when build_status == {status!r}.",
                expected="A specific failure reason.",
                fix="Set build_failure_reason to a load-bearing diagnosis.",
            ))
        elif reason.strip().lower() in _VACUOUS_REASONS:
            issues.append(_issue(
                description=f"{expected_id}/result.json: 'build_failure_reason' is vacuous: {reason!r}.",
                expected="A specific, load-bearing reason (not 'build failed', 'unknown error', etc.).",
                fix="Replace with a specific diagnosis (missing dep name, kernel feature, etc.).",
            ))

        if not _is_nonempty_string(data.get("attempts_summary")):
            issues.append(_issue(
                description=f"{expected_id}/result.json: 'attempts_summary' is required when build_status == {status!r}.",
                expected="A short summary of approaches tried.",
                fix="Set attempts_summary.",
            ))

    return issues
```

- [ ] **Step 8: Run Phase B tests**

Run: `pytest -q -k 'validate_stage2_phase_b'`
Expected: 9 PASS.

### 4.3 Final-manifest validator — TDD

- [ ] **Step 9: Write failing tests for the final-manifest validator**

Append:

```python
def test_validate_stage2_manifest_final_accepts_one_ok():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = os.path.join(tmp, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump({"configs": [
                {"id": "a", "build_status": "ok"},
                {"id": "b", "build_status": "infeasible"},
            ]}, f)
        assert validate_stage2_manifest_final(manifest_path) == []


def test_validate_stage2_manifest_final_warns_on_zero_ok():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = os.path.join(tmp, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump({"configs": [
                {"id": "a", "build_status": "infeasible"},
                {"id": "b", "build_status": "timeout"},
            ]}, f)
        issues = validate_stage2_manifest_final(manifest_path)
        assert any("no entries" in i.description.lower() and "ok" in i.description.lower() for i in issues)


def test_validate_stage2_manifest_final_missing_file():
    issues = validate_stage2_manifest_final("/nonexistent/manifest.json")
    assert any("manifest.json" in i.description.lower() for i in issues)
```

- [ ] **Step 10: Run tests to verify they fail**

Run: `pytest -q -k 'validate_stage2_manifest_final'`
Expected: 3 FAILs.

- [ ] **Step 11: Implement `validate_stage2_manifest_final` in `code_auditor/validation/stage2.py`**

Append:

```python
def validate_stage2_manifest_final(manifest_path: str) -> list[ValidationIssue]:
    """Validate the merged manifest after Phase B completes.

    Returns warnings (also as ValidationIssue) — the runner should not abort
    on these but should log them.
    """
    data, read_issues = _read_json(manifest_path)
    if read_issues:
        return read_issues

    if not isinstance(data, dict) or not isinstance(data.get("configs"), list):
        return [_issue(
            description="manifest.json: missing 'configs' array.",
            expected="A JSON object with a 'configs' array.",
            fix="Recreate the manifest from per-config result.json files.",
        )]

    configs = data["configs"]
    ok_count = sum(1 for entry in configs if isinstance(entry, dict) and entry.get("build_status") == "ok")
    if ok_count == 0:
        return [_issue(
            description="manifest.json: no entries have build_status == 'ok'.",
            expected="At least one successful build (warning).",
            fix="Investigate per-config result.json files; Stage 6 will fall back to ad-hoc building.",
        )]

    return []
```

- [ ] **Step 12: Run all stage2 validator tests**

Run: `pytest -q -k 'validate_stage2'`
Expected: 23 PASS.

- [ ] **Step 13: Run full test suite**

Run: `pytest -q`
Expected: all green.

- [ ] **Step 14: Commit**

```bash
git add code_auditor/validation/stage2.py code_auditor/tests/test_parsers_and_report.py
git commit -m "$(cat <<'EOF'
add validators for stage 2 (deployment realization)

Three validators: phase A (manifest + per-archetype deployment-mode),
phase B per-entry (result.json + scripts + artifact existence), and
final merged manifest (warns on zero successful builds).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Manifest merge helper (TDD)

The merge step folds each `configs/<id>/result.json` outcome into the corresponding manifest entry, downgrading malformed entries to `infeasible`.

**Files:**
- Create: `code_auditor/stages/stage2_deployments.py` (skeleton — only the merge function for now; the full runner is added in later tasks)
- Modify: `code_auditor/tests/test_parsers_and_report.py`

- [ ] **Step 1: Write failing test for happy-path merge**

Append:

```python
from code_auditor.stages.stage2_deployments import merge_results_into_manifest


def _phase_a_manifest_at(deployments_dir: str, ids: list[str]) -> str:
    os.makedirs(os.path.join(deployments_dir, "configs"), exist_ok=True)
    configs = [_phase_a_config(i) for i in ids]
    for cfg in configs:
        cfg["deployment_mode_path"] = f"configs/{cfg['id']}/deployment-mode.md"
    manifest_path = os.path.join(deployments_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump({"configs": configs}, f)
    return manifest_path


def _write_result(deployments_dir: str, cfg_id: str, result: dict) -> None:
    cfg_dir = os.path.join(deployments_dir, "configs", cfg_id)
    os.makedirs(cfg_dir, exist_ok=True)
    with open(os.path.join(cfg_dir, "result.json"), "w") as f:
        json.dump(result, f)


def test_merge_results_promotes_ok():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = _phase_a_manifest_at(tmp, ["a", "b"])
        artifact_a = os.path.join(tmp, "configs", "a", "build", "binA")
        os.makedirs(os.path.dirname(artifact_a), exist_ok=True)
        with open(artifact_a, "w") as f:
            f.write("x")
        for name in ("build.sh", "launch.sh", "smoke-test.sh"):
            p = os.path.join(tmp, "configs", "a", name)
            with open(p, "w") as f:
                f.write("#!/bin/sh\n")
            os.chmod(p, 0o755)
        _write_result(tmp, "a", {
            "id": "a",
            "build_status": "ok",
            "artifact_path": artifact_a,
            "launch_cmd": f"{tmp}/configs/a/launch.sh",
            "build_failure_reason": None,
            "attempts_summary": None,
        })
        _write_result(tmp, "b", {
            "id": "b",
            "build_status": "infeasible",
            "artifact_path": None,
            "launch_cmd": None,
            "build_failure_reason": "missing libfoo, no apt package available",
            "attempts_summary": "tried apt search libfoo; not packaged for this distro.",
        })
        merge_results_into_manifest(tmp)

        with open(manifest_path) as f:
            merged = json.load(f)
        by_id = {c["id"]: c for c in merged["configs"]}
        assert by_id["a"]["build_status"] == "ok"
        assert by_id["a"]["artifact_path"] == artifact_a
        assert by_id["b"]["build_status"] == "infeasible"
        assert by_id["b"]["build_failure_reason"]


def test_merge_results_downgrades_missing_result_json_to_infeasible():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = _phase_a_manifest_at(tmp, ["a"])
        os.makedirs(os.path.join(tmp, "configs", "a"), exist_ok=True)
        # No result.json written.
        merge_results_into_manifest(tmp)

        with open(manifest_path) as f:
            merged = json.load(f)
        a = merged["configs"][0]
        assert a["build_status"] == "infeasible"
        assert "result.json" in (a["build_failure_reason"] or "")


def test_merge_results_downgrades_malformed_result_to_infeasible():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = _phase_a_manifest_at(tmp, ["a"])
        cfg_dir = os.path.join(tmp, "configs", "a")
        os.makedirs(cfg_dir, exist_ok=True)
        # Write a malformed (missing build_status) result.json
        with open(os.path.join(cfg_dir, "result.json"), "w") as f:
            json.dump({"id": "a"}, f)
        merge_results_into_manifest(tmp)

        with open(manifest_path) as f:
            merged = json.load(f)
        a = merged["configs"][0]
        assert a["build_status"] == "infeasible"
        assert "result.json failed validation" in (a["build_failure_reason"] or "")


def test_merge_results_preserves_phase_a_entries_with_no_result_dir():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = _phase_a_manifest_at(tmp, ["a", "b"])
        # No configs/<id>/ dirs at all (Phase B never ran).
        merge_results_into_manifest(tmp)

        with open(manifest_path) as f:
            merged = json.load(f)
        assert {c["id"] for c in merged["configs"]} == {"a", "b"}
        for c in merged["configs"]:
            assert c["build_status"] == "infeasible"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest -q -k 'merge_results'`
Expected: 4 FAILs (`ImportError` because `stage2_deployments` does not exist yet).

- [ ] **Step 3: Create `code_auditor/stages/stage2_deployments.py` with the merge helper**

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from ..config import ValidationIssue
from ..logger import get_logger
from ..utils import format_validation_issues
from ..validation.stage2 import (
    validate_stage2_phase_b_entry,
)

logger = get_logger("stage2")


@dataclass
class DeploymentConfig:
    id: str
    name: str
    deployment_mode_path: str
    exposed_surface: list[str]
    modules_exercised: list[str]
    artifact_path: str | None
    launch_cmd: str | None


@dataclass
class Stage2Output:
    manifest_path: str
    deployment_summary_path: str
    configs: list[DeploymentConfig]


_RESULT_FIELDS = (
    "build_status",
    "artifact_path",
    "launch_cmd",
    "build_failure_reason",
    "attempts_summary",
)


def _load_manifest(manifest_path: str) -> dict:
    with open(manifest_path) as f:
        return json.load(f)


def _save_manifest(manifest_path: str, manifest: dict) -> None:
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def merge_results_into_manifest(deployments_dir: str) -> None:
    """Fold per-config result.json outcomes into manifest.json.

    Missing or malformed result.json entries are downgraded to
    build_status='infeasible' with a build_failure_reason describing the
    validation problem so downstream stages see consistent semantics.
    """
    manifest_path = os.path.join(deployments_dir, "manifest.json")
    manifest = _load_manifest(manifest_path)

    for entry in manifest.get("configs", []):
        cfg_id = entry.get("id")
        if not cfg_id:
            continue
        cfg_dir = os.path.join(deployments_dir, "configs", cfg_id)
        result_path = os.path.join(cfg_dir, "result.json")

        if not os.path.exists(result_path):
            entry["build_status"] = "infeasible"
            entry["build_failure_reason"] = "result.json missing — Phase B did not produce an outcome."
            entry["attempts_summary"] = entry.get("attempts_summary") or "n/a"
            entry.setdefault("artifact_path", None)
            entry.setdefault("launch_cmd", None)
            continue

        issues: list[ValidationIssue] = validate_stage2_phase_b_entry(cfg_dir)
        if issues:
            logger.warning(
                "Stage 2 merge: result.json for %s failed validation, downgrading to infeasible:\n%s",
                cfg_id, format_validation_issues(issues),
            )
            entry["build_status"] = "infeasible"
            entry["build_failure_reason"] = (
                f"result.json failed validation: {format_validation_issues(issues)}"
            )
            entry["attempts_summary"] = entry.get("attempts_summary") or "n/a"
            entry["artifact_path"] = None
            entry["launch_cmd"] = None
            continue

        with open(result_path) as f:
            data = json.load(f)
        for field in _RESULT_FIELDS:
            entry[field] = data.get(field)

    _save_manifest(manifest_path, manifest)
```

- [ ] **Step 4: Run merge tests**

Run: `pytest -q -k 'merge_results'`
Expected: 4 PASS.

- [ ] **Step 5: Run full suite**

Run: `pytest -q`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add code_auditor/stages/stage2_deployments.py code_auditor/tests/test_parsers_and_report.py
git commit -m "$(cat <<'EOF'
add manifest merge for stage 2 deployment outcomes

Folds per-config result.json into the merged manifest.json. Missing
or malformed entries are downgraded to build_status='infeasible' so
downstream stages see consistent semantics regardless of how a build
agent terminated.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Add `Stage2Output` builder helper

A small public helper that reads a merged manifest and returns the `Stage2Output` (only `ok` configs) used by the orchestrator.

**Files:**
- Modify: `code_auditor/stages/stage2_deployments.py`
- Modify: `code_auditor/tests/test_parsers_and_report.py`

- [ ] **Step 1: Write failing test**

Append:

```python
from code_auditor.stages.stage2_deployments import (
    Stage2Output,
    DeploymentConfig,
    load_stage2_output,
)


def test_load_stage2_output_filters_to_ok_only():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = _phase_a_manifest_at(tmp, ["a", "b"])
        # Make 'a' ok, 'b' infeasible.
        with open(manifest_path) as f:
            data = json.load(f)
        for c in data["configs"]:
            if c["id"] == "a":
                c["build_status"] = "ok"
                c["artifact_path"] = "/tmp/a"
                c["launch_cmd"] = "/tmp/a-launch"
            else:
                c["build_status"] = "infeasible"
                c["build_failure_reason"] = "x"
                c["attempts_summary"] = "y"
        with open(manifest_path, "w") as f:
            json.dump(data, f)

        # deployment-summary.md needed for path-checking
        with open(os.path.join(tmp, "deployment-summary.md"), "w") as f:
            f.write("summary")

        out = load_stage2_output(tmp)
        assert isinstance(out, Stage2Output)
        assert out.manifest_path == manifest_path
        assert out.deployment_summary_path.endswith("deployment-summary.md")
        assert len(out.configs) == 1
        assert out.configs[0].id == "a"
        assert out.configs[0].artifact_path == "/tmp/a"
        assert out.configs[0].launch_cmd == "/tmp/a-launch"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q -k 'load_stage2_output'`
Expected: FAIL (`ImportError`).

- [ ] **Step 3: Implement `load_stage2_output`**

Append to `code_auditor/stages/stage2_deployments.py`:

```python
def load_stage2_output(deployments_dir: str) -> Stage2Output:
    """Read a merged manifest and return only the entries with build_status == 'ok'."""
    manifest_path = os.path.join(deployments_dir, "manifest.json")
    summary_path = os.path.join(deployments_dir, "deployment-summary.md")
    manifest = _load_manifest(manifest_path)

    configs: list[DeploymentConfig] = []
    for entry in manifest.get("configs", []):
        if entry.get("build_status") != "ok":
            continue
        configs.append(DeploymentConfig(
            id=entry["id"],
            name=entry.get("name", ""),
            deployment_mode_path=os.path.join(deployments_dir, entry.get("deployment_mode_path", "")),
            exposed_surface=list(entry.get("exposed_surface", [])),
            modules_exercised=list(entry.get("modules_exercised", [])),
            artifact_path=entry.get("artifact_path"),
            launch_cmd=entry.get("launch_cmd"),
        ))
    return Stage2Output(
        manifest_path=manifest_path,
        deployment_summary_path=summary_path,
        configs=configs,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q -k 'load_stage2_output'`
Expected: PASS.

- [ ] **Step 5: Run full suite + commit**

Run: `pytest -q`
Expected: all green.

```bash
git add code_auditor/stages/stage2_deployments.py code_auditor/tests/test_parsers_and_report.py
git commit -m "$(cat <<'EOF'
add Stage2Output builder for orchestrator consumption

load_stage2_output(deployments_dir) returns only the configs with
build_status == 'ok' along with manifest + summary paths. Used by the
orchestrator to thread paths into stages 3, 4, and 6.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Phase A research function

Add the Phase A runner that calls the agent, validates the layout, and runs the one-shot repair pattern on validation failure.

**Files:**
- Modify: `code_auditor/stages/stage2_deployments.py`

- [ ] **Step 1: Add Phase A function to `code_auditor/stages/stage2_deployments.py`**

Add the new imports near the top of the file:

```python
from ..agent import run_agent
from ..checkpoint import CheckpointManager
from ..config import AuditConfig
from ..prompts import load_prompt
from ..validation.stage2 import (
    validate_stage2_phase_a,
    validate_stage2_manifest_final,
)
```

Add module-level constants near the top:

```python
_PHASE_A_TASK_KEY = "stage2:research"
_PHASE_A_MAX_TURNS = 200


def _phase_b_task_key(cfg_id: str) -> str:
    return f"stage2:build:{cfg_id}"
```

Append the function:

```python
async def _run_phase_a(
    config: AuditConfig,
    checkpoint: CheckpointManager,
    deployments_dir: str,
    auditing_focus_path: str,
) -> None:
    """Run the deployment research agent and validate its output."""
    if checkpoint.is_complete(_PHASE_A_TASK_KEY):
        logger.info("Stage 2 Phase A: already complete, skipping.")
        return

    os.makedirs(os.path.join(deployments_dir, "configs"), exist_ok=True)
    log_file = os.path.join(deployments_dir, "agent.log")

    research_record_path = os.path.join(
        config.output_dir, "stage1-security-context", "stage-1-security-context.json",
    )
    auditing_focus_str = auditing_focus_path

    prompt = load_prompt("stage2.md", {
        "target_path": config.target,
        "deployments_dir": deployments_dir,
        "configs_dir": os.path.join(deployments_dir, "configs"),
        "manifest_path": os.path.join(deployments_dir, "manifest.json"),
        "summary_path": os.path.join(deployments_dir, "deployment-summary.md"),
        "auditing_focus_path": auditing_focus_str,
        "research_record_path": research_record_path,
    })

    logger.info("Stage 2 Phase A: starting deployment research.")
    await run_agent(
        prompt,
        config,
        cwd=config.target,
        max_turns=_PHASE_A_MAX_TURNS,
        log_file=log_file,
    )

    issues = validate_stage2_phase_a(deployments_dir)
    if issues:
        logger.warning(
            "Stage 2 Phase A: validation issues:\n%s",
            format_validation_issues(issues),
        )
        repair_prompt = (
            f"The deployment manifest at `{deployments_dir}` failed validation. "
            "Please fix all issues listed below:\n\n"
            f"```\n{format_validation_issues(issues)}\n```"
        )
        await run_agent(
            repair_prompt, config, cwd=config.target,
            max_turns=10, log_file=log_file,
        )
        issues = validate_stage2_phase_a(deployments_dir)
        if issues:
            logger.warning(
                "Stage 2 Phase A: validation still failing after repair:\n%s",
                format_validation_issues(issues),
            )

    checkpoint.mark_complete(_PHASE_A_TASK_KEY)
    logger.info("Stage 2 Phase A: complete.")
```

- [ ] **Step 2: Run pytest to confirm no regressions**

Run: `pytest -q`
Expected: all green (the new function has no callers yet).

- [ ] **Step 3: Commit**

```bash
git add code_auditor/stages/stage2_deployments.py
git commit -m "$(cat <<'EOF'
add Phase A research runner for stage 2

Single agent that produces manifest.json + deployment-summary.md +
per-archetype deployment-mode.md. One-shot repair pass on validation
failure (mirrors existing stage 3 pattern).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Phase B build function + parallel runner

Per-config build agent with generous turn budget, wall-clock timeout, async cancel, and timeout fallback that writes a `result.json` if the agent didn't.

**Files:**
- Modify: `code_auditor/stages/stage2_deployments.py`

- [ ] **Step 1: Add Phase B helpers to `code_auditor/stages/stage2_deployments.py`**

Add asyncio + shutil imports near the top:

```python
import asyncio
import shutil
```

Update the existing utils import to also pull in `run_parallel_limited`:

```python
from ..utils import format_validation_issues, run_parallel_limited
```

Add constants:

```python
_PHASE_B_MAX_TURNS = 500
_PHASE_B_MODEL = "claude-opus-4-6"
_PHASE_B_EFFORT = "medium"
```

Append the Phase B helpers:

```python
def _write_timeout_result(cfg_dir: str, cfg_id: str, timeout_sec: int, log_path: str) -> None:
    """Write a result.json when a build agent timed out without producing one."""
    result = {
        "id": cfg_id,
        "build_status": "timeout",
        "artifact_path": None,
        "launch_cmd": None,
        "build_failure_reason": (
            f"Wall-clock timeout: build did not complete within {timeout_sec // 60} minutes."
        ),
        "attempts_summary": (
            "Build agent was cancelled by the runner after the timeout. "
            "See build.log for what was attempted."
        ),
    }
    os.makedirs(cfg_dir, exist_ok=True)
    with open(os.path.join(cfg_dir, "result.json"), "w") as f:
        json.dump(result, f, indent=2)
    if os.path.exists(log_path):
        try:
            shutil.copy2(log_path, os.path.join(cfg_dir, "build.log"))
        except OSError:
            pass


async def _run_one_build(
    entry: dict,
    config: AuditConfig,
    checkpoint: CheckpointManager,
    deployments_dir: str,
) -> None:
    cfg_id = entry["id"]
    key = _phase_b_task_key(cfg_id)
    cfg_dir = os.path.join(deployments_dir, "configs", cfg_id)
    deployment_mode_path = os.path.join(deployments_dir, entry["deployment_mode_path"])
    log_file = os.path.join(cfg_dir, "build.log")

    if checkpoint.is_complete(key):
        logger.info("Stage 2 Phase B: %s already complete, skipping.", cfg_id)
        return

    os.makedirs(cfg_dir, exist_ok=True)
    logger.info("Stage 2 Phase B: starting build for %s.", cfg_id)

    prompt = load_prompt("stage2-build.md", {
        "config_id": cfg_id,
        "deployment_mode_path": deployment_mode_path,
        "target_path": config.target,
        "config_dir": cfg_dir,
        "result_path": os.path.join(cfg_dir, "result.json"),
    })

    timed_out = False
    task = asyncio.create_task(
        run_agent(
            prompt, config, cwd=config.target,
            max_turns=_PHASE_B_MAX_TURNS,
            model=_PHASE_B_MODEL,
            effort=_PHASE_B_EFFORT,
            log_file=log_file,
        )
    )
    done, _ = await asyncio.wait({task}, timeout=config.deployment_build_timeout_sec)

    if not done:
        timed_out = True
        task.cancel()
        grace_done, _ = await asyncio.wait({task}, timeout=30)
        if not grace_done:
            logger.warning(
                "Stage 2 Phase B: %s agent task did not exit after cancel, moving on.",
                cfg_id,
            )
        logger.warning(
            "Stage 2 Phase B: %s timed out after %d minutes.",
            cfg_id, config.deployment_build_timeout_sec // 60,
        )
    else:
        exc = task.exception()
        if exc is not None:
            raise exc

    result_path = os.path.join(cfg_dir, "result.json")
    if timed_out and not os.path.exists(result_path):
        _write_timeout_result(cfg_dir, cfg_id, config.deployment_build_timeout_sec, log_file)

    checkpoint.mark_complete(key)
    logger.info("Stage 2 Phase B: %s complete (timed_out=%s).", cfg_id, timed_out)


async def _run_phase_b(
    config: AuditConfig,
    checkpoint: CheckpointManager,
    deployments_dir: str,
) -> None:
    """Run one build agent per archetype, capped by deployment_build_parallel."""
    manifest = _load_manifest(os.path.join(deployments_dir, "manifest.json"))
    entries = list(manifest.get("configs", []))
    if not entries:
        logger.warning("Stage 2 Phase B: manifest has no configs; nothing to build.")
        return

    logger.info(
        "Stage 2 Phase B: launching %d build agents (parallel cap: %d).",
        len(entries), config.deployment_build_parallel,
    )
    await run_parallel_limited(
        entries,
        config.deployment_build_parallel,
        lambda entry, _idx: _run_one_build(entry, config, checkpoint, deployments_dir),
    )
```

- [ ] **Step 2: Add `run_stage2_deployments` orchestration entry point**

Append:

```python
async def run_stage2_deployments(
    config: AuditConfig,
    checkpoint: CheckpointManager,
    auditing_focus_path: str,
) -> Stage2Output:
    deployments_dir = os.path.join(config.output_dir, "stage2-deployments")
    os.makedirs(deployments_dir, exist_ok=True)
    os.makedirs(os.path.join(deployments_dir, "configs"), exist_ok=True)

    await _run_phase_a(config, checkpoint, deployments_dir, auditing_focus_path)
    await _run_phase_b(config, checkpoint, deployments_dir)

    merge_results_into_manifest(deployments_dir)

    final_issues = validate_stage2_manifest_final(
        os.path.join(deployments_dir, "manifest.json"),
    )
    for issue in final_issues:
        logger.warning("Stage 2 final manifest: %s", issue.description)

    output = load_stage2_output(deployments_dir)
    logger.info(
        "Stage 2 complete. %d archetype(s) with build_status='ok'.",
        len(output.configs),
    )
    return output
```

- [ ] **Step 3: Run pytest**

Run: `pytest -q`
Expected: still green (no callers yet).

- [ ] **Step 4: Commit**

```bash
git add code_auditor/stages/stage2_deployments.py
git commit -m "$(cat <<'EOF'
add Phase B build runner + stage 2 entry point

Per-config build agent with generous turn budget and wall-clock timeout.
On timeout the runner writes a result.json with build_status='timeout'
so the merge step has consistent semantics. Parallelism is capped by
config.deployment_build_parallel (separate from --max-parallel).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Phase A prompt — `prompts/stage2.md`

**Files:**
- Create: `prompts/stage2.md`

- [ ] **Step 1: Write the prompt**

Create `prompts/stage2.md` with this content:

````markdown
# Stage 2: Deployment Realization — Phase A (Research)

You are performing **Phase A of Stage 2** of an orchestrated software security audit. Your job is to investigate how the target project is actually deployed in production and to enumerate 1–N **deployment archetypes** that materially differ in attack surface. **Write your output to disk; do not print it in your response.** Phase B (a separate agent invocation) will later realize each archetype as a runnable instrumented build.

## Your Task

Research the project at **__TARGET_PATH__** and produce:

1. A **manifest** at `__MANIFEST_PATH__` listing every archetype.
2. A **deployment summary** at `__SUMMARY_PATH__` — one short paragraph per archetype, suitable for injection into downstream analysis prompts.
3. One **deployment mode** description per archetype at `__CONFIGS_DIR__/<config-id>/deployment-mode.md`.

Prior research is available at:
- Auditing focus: `__AUDITING_FOCUS_PATH__`
- Stage 1 research record: `__RESEARCH_RECORD_PATH__` (the `deployment_model` field is a useful starting point).

## Workflow

### Step 1: Investigate Real-World Deployments

Read the project's documentation, examples, upstream Dockerfiles, distro packaging, and any deployment guides you can find on the project website. Identify the distinct *roles* the target is run in (e.g. for an HTTP server: "static web server with TLS", "reverse proxy", "CGI host"). Each archetype must materially differ in attack surface — different exposed interfaces, different code paths, different configuration footprint.

**Each archetype must be grounded in evidence found during research.** Do not invent archetypes the project does not actually support.

### Step 2: Define Archetypes

For each archetype, decide:
- A short kebab-case `id` (lowercase, hyphenated). Example: `httpd-static-tls`.
- A human-readable `name`.
- The `exposed_surface` — the kinds of interfaces this deployment exposes to attackers (e.g. "http parser", "tls handshake", "mod_ssl").
- The `modules_exercised` — relative source paths (directories or files) that this deployment uses at runtime (e.g. `server/`, `modules/ssl/`).

### Step 3: Write the Deployment Mode Files

For each archetype, write `__CONFIGS_DIR__/<id>/deployment-mode.md` describing:
- The role the target plays.
- The network/IPC surface it exposes (ports, sockets, IPC channels, files watched, etc.).
- The kinds of inputs it processes from the outside world.
- A behavioral contract the smoke test must satisfy: "when this deployment is launched, sending input X to interface Y must produce response Z." Be specific enough that Phase B's smoke test can mechanically verify it.

**Do not write any of `build.sh`, `launch.sh`, `smoke-test.sh`** — those belong to Phase B.

### Step 4: Write the Manifest

Write `__MANIFEST_PATH__` with this schema:

```json
{
  "configs": [
    {
      "id": "httpd-static-tls",
      "name": "Static web server with TLS",
      "deployment_mode_path": "configs/httpd-static-tls/deployment-mode.md",
      "exposed_surface": ["http parser", "tls handshake", "mod_ssl"],
      "modules_exercised": ["server/", "modules/ssl/", "modules/http/"],
      "build_status": null,
      "artifact_path": null,
      "launch_cmd": null,
      "build_failure_reason": null,
      "attempts_summary": null
    }
  ]
}
```

The `build_*` and `artifact_*` and `launch_cmd` and `attempts_summary` fields **must all be null** after Phase A — Phase B fills them.

### Step 5: Write the Deployment Summary

Write `__SUMMARY_PATH__` — one short paragraph per archetype covering: role, exposed surface, modules exercised. This text is injected into downstream prompts (stages 3, 4, and 6) to bias analysis toward production-reachable code.

## Constraints

- 1 to N archetypes; pick the smallest set that captures distinct attack surfaces.
- All ids are unique kebab-case.
- `exposed_surface` and `modules_exercised` must be non-empty for every archetype.
- Every `deployment_mode_path` must point at a non-empty file you actually wrote.

## Completion Checklist

- [ ] Project documentation, examples, distro packaging consulted
- [ ] At least one archetype defined and grounded in evidence
- [ ] `__MANIFEST_PATH__` written with all build fields null
- [ ] `__SUMMARY_PATH__` written
- [ ] Each archetype has a non-empty `deployment-mode.md`
- [ ] No `build.sh`, `launch.sh`, or `smoke-test.sh` written (those are Phase B's job)
````

- [ ] **Step 2: Run pytest**

Run: `pytest -q`
Expected: still green.

- [ ] **Step 3: Commit**

```bash
git add prompts/stage2.md
git commit -m "$(cat <<'EOF'
add Phase A prompt for stage 2 deployment research

Single-agent prompt: investigate real-world deployments, define 1-N
archetypes grounded in evidence, write manifest + per-archetype
deployment-mode.md + injected summary. Build artifacts are explicitly
out of scope for this phase.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Phase B prompt — `prompts/stage2-build.md`

**Files:**
- Create: `prompts/stage2-build.md`

- [ ] **Step 1: Write the prompt**

Create `prompts/stage2-build.md`:

````markdown
# Stage 2: Deployment Realization — Phase B (Build)

You are performing **Phase B of Stage 2** of an orchestrated software security audit. Your job is to **realize a specific deployment archetype as a runnable, instrumented build** of the target.

**Write your output to disk; do not print it in your response.**

## Inputs

- **Config id**: `__CONFIG_ID__`
- **Deployment mode** (Phase A description of role + exposed surface + behavioral contract): `__DEPLOYMENT_MODE_PATH__`
- **Target source tree**: `__TARGET_PATH__`
- **Working directory** (write all artifacts here): `__CONFIG_DIR__`
- **Result file path** (must exist when you finish): `__RESULT_PATH__`

## Workflow

### Step 1: Plan

Read `__DEPLOYMENT_MODE_PATH__` carefully. Decide:
- The build approach (configure flags, compile flags, container vs. bare-metal) consistent with the archetype's role and behavioral contract.
- Sanitizer/debug instrumentation appropriate for the language and build system. **Always include sanitizers** (e.g. `-fsanitize=address,undefined` for C/C++; race detector for Go; equivalent for other languages). The artifact must be instrumented so downstream PoC reproduction captures high-quality evidence.

### Step 2: Author Build Scripts

Write the following executable scripts in `__CONFIG_DIR__`:
- `build.sh` — builds the target into the requested archetype with instrumentation. Idempotent if possible.
- `launch.sh` — launches the artifact with the configuration appropriate for this archetype (e.g. `httpd -f .../httpd.conf`). The launch command should be self-contained and deterministic.
- `smoke-test.sh` — exercises the behavioral contract from `deployment-mode.md`. Exits 0 on success, non-zero on failure. Has bounded runtime (e.g. timeout 30s).

Make all three scripts executable (`chmod +x`).

### Step 3: Build

Run `build.sh`. **Iterate on failures** within your turn budget: install missing dependencies (using package managers available in this environment), adjust configure/compile flags, debug build errors. Do not give up after the first failure.

If a system dependency cannot be installed in this environment (no apt package, no pip wheel, no available source build), or if the deployment requires hardware/kernel features not present, or if the upstream build system is broken at this revision and not patchable without source modification, conclude **infeasible** and document the *specific* load-bearing reason.

### Step 4: Smoke Test

Once the build succeeds, launch the artifact with `launch.sh` and run `smoke-test.sh` against it. The contract from `deployment-mode.md` must be satisfied. If it isn't, that's a build problem — iterate.

### Step 5: Write `__RESULT_PATH__`

Write the result as a single JSON object with this exact schema:

```json
{
  "id": "__CONFIG_ID__",
  "build_status": "ok | infeasible | timeout",
  "artifact_path": "absolute path to the launchable artifact, or null",
  "launch_cmd": "shell command (or path to launch.sh), or null",
  "build_failure_reason": "specific load-bearing reason, or null",
  "attempts_summary": "short summary of approaches tried, or null"
}
```

Rules:
- For `build_status == "ok"`: `artifact_path` and `launch_cmd` must be non-null. `build_failure_reason` must be null.
- For `build_status == "infeasible"`: `build_failure_reason` and `attempts_summary` must be non-null and **specific** — not "build failed", "unknown error", "failed", or "error". Name the missing dep, the absent kernel feature, the unavailable license, etc.
- The runner sets `build_status == "timeout"` automatically if you don't finish in time. You should not write `"timeout"` yourself unless the deployment's smoke test cannot terminate even after a successful build (rare edge case).

## Forbidden actions

- Do not patch the source code. If reproduction requires source changes, that's an `infeasible` outcome — document the change that would be needed.
- Do not install to system directories outside this environment.
- Do not bypass safety mechanisms (e.g. forging signatures, faking artifact existence). The runner re-validates artifact_path on disk.

## Completion Checklist

- [ ] `build.sh`, `launch.sh`, `smoke-test.sh` written and chmod +x
- [ ] Build attempted with sanitizers/instrumentation
- [ ] Behavioral contract from deployment-mode.md exercised by smoke-test.sh
- [ ] `__RESULT_PATH__` written with one of: ok / infeasible
- [ ] If infeasible: `build_failure_reason` is specific and load-bearing; `attempts_summary` documents what was tried
````

- [ ] **Step 2: Run pytest**

Run: `pytest -q`
Expected: still green.

- [ ] **Step 3: Commit**

```bash
git add prompts/stage2-build.md
git commit -m "$(cat <<'EOF'
add Phase B prompt for stage 2 deployment build

Per-config build agent prompt: author build/launch/smoke scripts,
build with sanitizers, validate behavioral contract, write result.json.
Iteration is the agent's responsibility within its turn budget; the
runner enforces a wall-clock timeout.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Wire Stage 2 into the orchestrator

**Files:**
- Modify: `code_auditor/orchestrator.py`

- [ ] **Step 1: Add the Stage 2 import + invocation in `code_auditor/orchestrator.py`**

Add the import near the top:

```python
from .stages.stage2_deployments import Stage2Output, run_stage2_deployments
```

In `run_audit()`, replace the placeholder `# Stage 2 (deployment realization) is wired in Task 11.` with:

```python
    stage2_out: Stage2Output | None = None
    if 2 not in config.skip_stages:
        stage2_out = await run_stage2_deployments(config, checkpoint, auditing_focus_path)

    deployments_dir = os.path.join(config.output_dir, "stage2-deployments")
    deployment_summary_path = (
        stage2_out.deployment_summary_path if stage2_out
        else os.path.join(deployments_dir, "deployment-summary.md")
    )
    deployment_manifest_path = (
        stage2_out.manifest_path if stage2_out
        else os.path.join(deployments_dir, "manifest.json")
    )
```

The `deployment_summary_path` and `deployment_manifest_path` variables will be threaded into stages 3, 4, and 6 by Tasks 12, 13, and 14. For now they are unused after the assignment — that's OK; pytest doesn't fail on unused variables.

- [ ] **Step 2: Run pytest**

Run: `pytest -q`
Expected: still green.

- [ ] **Step 3: Commit**

```bash
git add code_auditor/orchestrator.py
git commit -m "$(cat <<'EOF'
wire stage 2 (deployment realization) into the orchestrator

Adds the run_stage2_deployments call between stage 1 and stage 3,
and resolves deployment_summary_path + deployment_manifest_path for
threading into downstream stages.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Inject deployment summary into Stage 3 (AU decomposition)

**Files:**
- Modify: `code_auditor/stages/stage3.py`
- Modify: `code_auditor/orchestrator.py`
- Modify: `prompts/stage3.md`

- [ ] **Step 1: Add `__DEPLOYMENT_SUMMARY__` placeholder + section to `prompts/stage3.md`**

Open `prompts/stage3.md`. Find the section block:

```markdown
## Auditing Focus

### Explicit In-Scope and Out-of-Scope Modules

__SCOPE_MODULES__

### Historical Hot Spots

__HISTORICAL_HOT_SPOTS__
```

Insert immediately after that block (and before `## Workflow`):

```markdown
## Real-World Deployment Surfaces

The following deployment archetypes were identified for this project. When decomposing into analysis units, prioritize modules that are exercised in these deployments and on the externally exposed surface. Modules unreachable in any of these archetypes can be deprioritized or grouped into lower-priority AUs.

__DEPLOYMENT_SUMMARY__
```

- [ ] **Step 2: Thread `deployment_summary_path` through `run_stage3`**

Edit `code_auditor/stages/stage3.py`. Add a parameter to `run_stage3`:

```python
async def run_stage3(
    config: AuditConfig,
    checkpoint: CheckpointManager,
    auditing_focus_path: str,
    deployment_summary_path: str,
) -> list[AnalysisUnit]:
```

Inside the function, before `prompt = load_prompt(...)`, add:

```python
    deployment_summary = ""
    if os.path.exists(deployment_summary_path):
        with open(deployment_summary_path) as f:
            deployment_summary = f.read().strip()
```

Then update the `load_prompt` call to include the new key:

```python
    prompt = load_prompt("stage3.md", {
        "target_path": config.target,
        "result_dir": result_dir,
        "user_instructions": config.scope or "No additional scope constraints.",
        "scope_modules": scope_modules or "No scope information available.",
        "historical_hot_spots": hot_spots or "No historical data available.",
        "target_au_count": str(config.target_au_count),
        "deployment_summary": deployment_summary or "No deployment summary available.",
    })
```

- [ ] **Step 3: Update the orchestrator call**

In `code_auditor/orchestrator.py`, change the Stage 3 call to:

```python
    if 3 not in config.skip_stages:
        analysis_units = await run_stage3(
            config, checkpoint, auditing_focus_path, deployment_summary_path,
        )
```

- [ ] **Step 4: Run pytest**

Run: `pytest -q`
Expected: still green.

- [ ] **Step 5: Commit**

```bash
git add code_auditor/stages/stage3.py code_auditor/orchestrator.py prompts/stage3.md
git commit -m "$(cat <<'EOF'
inject deployment summary into stage 3 (AU decomposition)

Additive prompt input: AU selection biased toward modules exercised
in real-world deployments. Falls back to a placeholder when stage 2
produced no summary.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Inject deployment summary into Stage 4 (bug discovery)

**Files:**
- Modify: `code_auditor/stages/stage4.py`
- Modify: `code_auditor/orchestrator.py`
- Modify: `prompts/stage4.md`

- [ ] **Step 1: Add `__DEPLOYMENT_SUMMARY__` placeholder + section to `prompts/stage4.md`**

Open `prompts/stage4.md`. After the existing "## Your Assignment" block (which currently directs the agent to read auditing focus + vuln criteria) and before the analysis unit instructions, insert:

```markdown
## Real-World Reachability Context

The deployment archetypes below describe how this code is run in production. When evaluating a candidate bug, prefer ones reachable from these deployment entry points. A bug only reachable from code that runs in no archetype is lower-confidence.

__DEPLOYMENT_SUMMARY__
```

- [ ] **Step 2: Thread `deployment_summary_path` through `run_stage4` + `_run_unit`**

Edit `code_auditor/stages/stage4.py`. Add a `deployment_summary_path` parameter to both `_run_unit` and `run_stage4`:

```python
async def _run_unit(
    unit: AnalysisUnit,
    config: AuditConfig,
    checkpoint: CheckpointManager,
    auditing_focus_path: str,
    vuln_criteria_path: str,
    deployment_summary_path: str,
    unit_index: int = 0,
    total_units: int = 0,
) -> list[str]:
```

```python
async def run_stage4(
    units: list[AnalysisUnit],
    config: AuditConfig,
    checkpoint: CheckpointManager,
    auditing_focus_path: str,
    vuln_criteria_path: str,
    deployment_summary_path: str,
) -> list[str]:
```

Inside `_run_unit`, before `prompt = load_prompt(...)`:

```python
    deployment_summary = ""
    if os.path.exists(deployment_summary_path):
        with open(deployment_summary_path) as f:
            deployment_summary = f.read().strip()
```

Add `"deployment_summary": deployment_summary or "No deployment summary available."` to the `load_prompt` substitution dict.

Update the `run_parallel_limited` call to forward `deployment_summary_path`:

```python
    results = await run_parallel_limited(
        units,
        config.max_parallel,
        lambda unit, idx: _run_unit(
            unit, config, checkpoint, auditing_focus_path, vuln_criteria_path,
            deployment_summary_path,
            unit_index=idx + 1, total_units=total,
        ),
    )
```

- [ ] **Step 3: Update orchestrator call**

In `code_auditor/orchestrator.py`:

```python
    if 4 not in config.skip_stages:
        bug_files = await run_stage4(
            analysis_units, config, checkpoint,
            auditing_focus_path, vuln_criteria_path, deployment_summary_path,
        )
```

- [ ] **Step 4: Run pytest**

Run: `pytest -q`
Expected: still green.

- [ ] **Step 5: Commit**

```bash
git add code_auditor/stages/stage4.py code_auditor/orchestrator.py prompts/stage4.md
git commit -m "$(cat <<'EOF'
inject deployment summary into stage 4 (bug discovery)

Discovery agents see real-world reachability context per AU; guidance
only, not a hard filter. Real reachability is empirically tested in
stage 6 against the live deployment.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Stage 6 (PoC) — Step 0 selection, drop Step 4, thread manifest path

**Files:**
- Modify: `code_auditor/stages/stage6.py`
- Modify: `code_auditor/orchestrator.py`
- Modify: `prompts/stage6.md`

- [ ] **Step 1: Edit `prompts/stage6.md` — add Step 0 and remove Step 4**

Open `prompts/stage6.md`. Near the input/finding-file section at the top, add new placeholder lines documenting the new inputs:

```markdown
- **Deployment manifest** (pre-built artifacts to choose from): `__DEPLOYMENT_MANIFEST_PATH__`
- **Deployments directory** (for reading per-config deployment-mode.md if needed): `__DEPLOYMENTS_DIR__`
```

Above the existing "### Step 1: Design the Reproduction Strategy" header, insert:

```markdown
### Step 0: Select a Pre-Built Deployment

Read `__DEPLOYMENT_MANIFEST_PATH__`. From entries with `build_status == "ok"`, pick the single config whose `exposed_surface` and `modules_exercised` best match this finding's location and trigger. State your choice and one-sentence reasoning. Use the config's `launch_cmd` to start the artifact under `__POC_DIR__`. Do not rebuild — the artifact is already instrumented.

If no entry has `build_status == "ok"`, fall back to building from source per the original instructions in Step 1 and note this fallback in the report.
```

Delete the entire `### Step 4: Real-World Exploitability Assessment` section (the content currently spans roughly 14 lines including its bullet list explaining timing/race-window/non-default-config heuristics). The judgment it asks the LLM to make is now empirical — attacking the live pre-built deployment. Keep `Reproduction Status: false-positive` as a valid outcome label in Step 5.

After deleting Step 4, renumber the subsequent sections (Step 5 → Step 4, Step 6 → Step 5) so the prompt stays coherent. Update any internal back-references (e.g. "proceed to Step 5") to the new numbers.

- [ ] **Step 2: Thread `deployment_manifest_path` and `deployments_dir` through `run_stage6`**

Edit `code_auditor/stages/stage6.py`. Add the two new parameters to both `_run_reproduce` and `run_stage6`:

```python
async def _run_reproduce(
    vuln_file_path: str,
    config: AuditConfig,
    checkpoint: CheckpointManager,
    deployment_manifest_path: str,
    deployments_dir: str,
) -> str | None:
```

```python
async def run_stage6(
    vuln_files: list[str],
    config: AuditConfig,
    checkpoint: CheckpointManager,
    deployment_manifest_path: str,
    deployments_dir: str,
) -> list[str]:
```

Update the `load_prompt` call in `_run_reproduce`:

```python
    prompt = load_prompt("stage6.md", {
        "finding_file_path": vuln_file_path,
        "target_path": config.target,
        "poc_dir": poc_dir,
        "finding_id": vuln_id,
        "deployment_manifest_path": deployment_manifest_path,
        "deployments_dir": deployments_dir,
    })
```

Update the `run_parallel_limited` call inside `run_stage6`:

```python
    results = await run_parallel_limited(
        vuln_files,
        config.max_parallel,
        lambda vf, _: _run_reproduce(
            vf, config, checkpoint,
            deployment_manifest_path, deployments_dir,
        ),
    )
```

- [ ] **Step 3: Update the orchestrator call**

In `code_auditor/orchestrator.py`, update the Stage 6 invocation:

```python
    if 6 not in config.skip_stages:
        stage6_reports = await run_stage6(
            vuln_files, config, checkpoint,
            deployment_manifest_path, deployments_dir,
        )
```

- [ ] **Step 4: Run pytest**

Run: `pytest -q`
Expected: still green.

- [ ] **Step 5: Commit**

```bash
git add code_auditor/stages/stage6.py code_auditor/orchestrator.py prompts/stage6.md
git commit -m "$(cat <<'EOF'
stage 6 PoC selects pre-built deployment + drops LLM exploitability gate

Step 0 picks the best-matching pre-built artifact from the stage 2
manifest and uses it directly (no rebuild). Step 4's pure-LLM
'realistic exploit?' check is removed — that judgment is now
empirical (the PoC either triggers against the production-like
artifact, or it doesn't).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: Update README.md and CLAUDE.md

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update README.md stage table**

Open `README.md`. Replace the existing seven-row stage table (rows 0–6) with this eight-row table covering 0–7:

```markdown
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
```

- [ ] **Step 2: Add the new flag to README's options table**

In the "Common options" table, add a row:

```markdown
| `--deployment-build-parallel` | Max concurrent stage-2 build agents (default: `1`). Separate from `--max-parallel` because builds are CPU/RAM heavy. |
| `--deployment-build-timeout-sec` | Wall-clock seconds per stage-2 build agent (default: `1800`). |
```

- [ ] **Step 3: Update README's output layout section**

Replace the output tree with the new structure:

```markdown
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

- [ ] **Step 4: Add a one-line resume-incompatibility note**

Below the existing "Runs resume from checkpoint markers automatically — delete the output directory…" sentence, add:

```markdown
Existing audit outputs created before the deployment-realization stage was added are stage-numbered under the old scheme; they will not resume cleanly with the current code. Either finish them on the previous version or start fresh.
```

- [ ] **Step 5: Update README's "Project layout" section**

In the layout block, change the lines about `stages/` and `prompts/` to reflect the new range:

```markdown
├── stages/              # stage0 – stage7
…
prompts/                 # stage1.md, stage2.md, stage2-build.md, stage3.md – stage7.md
```

- [ ] **Step 6: Update CLAUDE.md**

`CLAUDE.md` is currently stale (mentions removed flags `--skip-stages`, `--only-stage`, `--threat-model`, `--scope`). Rewrite the "Running" block to drop those flags and add the two new ones, and rewrite the architecture table to match the eight-row layout from Step 1. Specifically:

- Replace the "Running" code block with one that shows only flags actually exposed by `__main__.py` (`--target`, `--output-dir`, `--max-parallel`, `--model`, `--target-au-count`, `--log-level`, plus the two new `--deployment-build-*` flags).
- Replace the seven-row architecture table with the eight-row table from Step 1.
- In the "Project layout" section, change `stages/` comment to `# stage0–stage7`, update `validation/` to `# common.py + stage1–stage7`, and update `prompts/` line to `# stage1.md, stage2.md, stage2-build.md, stage3.md–stage7.md`.
- In the "Key patterns / Directive injection" line, mention deployment summary as a third directive injected into stages 3, 4, and 6.
- In "Output dir layout", swap the path list for the new one from Step 3.

- [ ] **Step 7: Run pytest**

Run: `pytest -q`
Expected: still green (docs-only changes).

- [ ] **Step 8: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: update README and CLAUDE.md for stage 2 + renumbered pipeline

New 8-stage table, deployment_build flags, output layout, project
layout. CLAUDE.md cleanup: drop stale --skip-stages / --only-stage /
--threat-model / --scope references that the current __main__.py no
longer exposes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: Final verification

**Files:** none modified.

- [ ] **Step 1: Run full test suite**

Run: `pytest -q`
Expected: all green.

- [ ] **Step 2: Verify CLI help renders**

Run: `code-auditor --help 2>&1 | head -40`
Expected: output includes `--deployment-build-parallel` and `--deployment-build-timeout-sec` with their help text.

- [ ] **Step 3: Verify prompt placeholder substitution surface**

Run: `grep -n '__DEPLOYMENT_SUMMARY__\|__DEPLOYMENT_MANIFEST_PATH__\|__DEPLOYMENTS_DIR__' prompts/*.md`
Expected matches:
- `prompts/stage3.md` and `prompts/stage4.md`: `__DEPLOYMENT_SUMMARY__`
- `prompts/stage6.md`: `__DEPLOYMENT_MANIFEST_PATH__` and `__DEPLOYMENTS_DIR__`

If any expected match is missing, return to the appropriate task and fix.

- [ ] **Step 4: Verify checkpoint manager handles all new keys**

Run: `python -c "from code_auditor.checkpoint import CheckpointManager; m = CheckpointManager('/tmp/x', resume=True); print(m._resolve('stage2:research')); print(m._resolve('stage2:build:abc')); print(m._resolve('stage3')); print(m._resolve('stage7:V-01'))"`
Expected: four non-`None` paths printed (each pointing under `/tmp/x/.markers/...` or for stage1's case the well-known JSON file), and no "Unknown checkpoint task key" warnings on stderr.

- [ ] **Step 5: Verify the renumbered output directory list is consistent**

Run: `grep -n 'stage._-' code_auditor/stages/stage0.py`
Expected: lines reference `stage1-security-context`, `stage2-deployments`, `stage2-deployments/configs`, `stage3-analysis-units`, `stage4-findings`, `stage5-vulnerabilities`, `stage5-vulnerabilities/_pending`, `stage6-pocs`, `stage7-disclosures`. No `stage2-analysis-units`, `stage3-findings`, `stage4-vulnerabilities`, `stage5-pocs`, `stage6-disclosures`.

- [ ] **Step 6: Final summary**

Report to the user:
- Pytest result
- That all 16 tasks completed cleanly
- Suggested next step: a smoke run on a small target project to confirm end-to-end behavior (out of scope for unit tests since stage 2 makes real agent calls).

No commit needed for this task.

---

## Notes on partial execution and resume

This plan is structured so that each task ends with a green pytest and a commit. If execution is interrupted, the next run can resume at the next task without rework. The renumber in Task 2 is the largest atomic step; once it lands cleanly, every subsequent task is incremental.

If Task 2 fails partway through, the safest recovery is `git reset --hard HEAD` (only after confirming no other unrelated work is in the working tree) and restart Task 2 from Step 1.
