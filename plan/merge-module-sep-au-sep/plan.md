# Plan: Merge Module Decomposition (Stage 2) and AU Splitting (Stage 3)

## Motivation

Currently the codebase is loaded into an agent's context window twice:

1. **Stage 2** — one agent reads the entire codebase, groups files into coarse functional modules (`M-1`, `M-2`, ...).
2. **Stage 3** — one agent *per module* re-reads the module's files, measures LOC, and splits large modules into fine-grained analysis units (`AU-1`, `AU-2`, ...).

By instructing the Stage 2 agent to produce modules at AU granularity directly (500-1500 LOC, 2-8 files each), every module **is** an analysis unit. Stage 3 becomes unnecessary.

## Current data flow

```
Stage 2 (1 agent)           Stage 3 (N agents)           Stage 4 (M agents)
─────────────────           ──────────────────           ──────────────────
Codebase → modules.json  →  per-module AU files      →   per-AU findings
                             + renumber to AU-{N}
```

## Proposed data flow

```
Stage 1 (1 agent)        Merged Stage 2 (1 agent)              Stage 4 (M agents)
─────────────────        ────────────────────────              ──────────────────
research → auditing  ──→ Codebase + auditing focus          → per-AU findings
           focus             → AU files (AU-1.json, ...)
```

---

## Changes required

### 1. New prompt: `prompts/stage2.md` (rewrite in place)

Merge the guidance from current `stage2.md` and `stage3.md` into one prompt. Key instructions:

- Enumerate all source files (same exclusions as current stage 2: tests, build artifacts, generated code, vendored deps).
- Understand the project via README, build config, top-level code.
- Group files into analysis units based on functionality, guided by the auditing focus. The agent determines appropriate unit sizing based on code structure and security relevance — no hardcoded LOC thresholds in the prompt.
- Out-of-scope code (per the auditing focus) does not need to be included in any AU.
- Output: write one JSON file per unit to `__RESULT_DIR__/AU-{N}.json`.
- AU JSON format (extended from current stage 3 output with `analyze` field):
  ```json
  {
    "description": "What this unit covers",
    "files": ["relative/path/file1.c", ...],
    "focus": "Concrete analysis guidance: name functions, data flows, complex areas, external input handling",
    "analyze": true
  }
  ```
- After producing all AUs, a selection step sets `analyze` to `true` or `false` per unit. At most **50** units may have `analyze: true`. Priority goes to in-scope modules, historical hot spots, external input handling, and security-critical code.
- Also write a summary file `__RESULT_DIR__/project-summary.json`:
  ```json
  {
    "project_summary": "...",
    "au_count": N
  }
  ```

Placeholders needed:
- `__TARGET_PATH__` — project root
- `__RESULT_DIR__` — output directory for AU files
- `__USER_INSTRUCTIONS__` — user scope constraints
- `__SCOPE_MODULES__` — content of the "Explicit In-Scope and Out-of-Scope Modules" section from the stage 1 auditing focus directive
- `__HISTORICAL_HOT_SPOTS__` — content of the "Historical Hot Spots" section from the stage 1 auditing focus directive

Remove `__OUTPUT_PATH__` (single JSON file) and `__STAGE2_OUTPUT_PATH__`, `__MODULE_ID__` (stage 3 leftovers).

**Auditing focus injection (new).** Stage 1 produces an auditing focus directive with two sections: scope modules and historical hot spots. The stage runner reads the directive file, extracts each section's content, and injects them into the prompt via `__SCOPE_MODULES__` and `__HISTORICAL_HOT_SPOTS__` placeholders. This guides decomposition:
- Hot-spot components get finer-grained AUs.
- Out-of-scope code can be excluded from analysis entirely.
- The `focus` field of each AU should echo relevant hot-spot patterns so the downstream stage 4 agent knows what to prioritize.

Currently the auditing focus is only injected into stage 4. After this change it is injected into **both** stage 2 and stage 4.

### 2. Stage runner: rewrite `stages/stage2.py`

Current stage 2 runs one agent and writes a single `stage-2-modules.json`. New behavior:

```python
async def run_stage2(config, checkpoint, auditing_focus_path) -> list[AnalysisUnit]:
    result_dir = os.path.join(config.output_dir, "stage-2-details")
    os.makedirs(result_dir, exist_ok=True)

    # Read directive file and extract the two sections
    scope_modules, hot_spots = parse_auditing_focus(auditing_focus_path)

    prompt = load_prompt("stage2.md", {
        "TARGET_PATH": config.target,
        "RESULT_DIR": result_dir,
        "USER_INSTRUCTIONS": config.scope or "No additional scope constraints.",
        "SCOPE_MODULES": scope_modules or "No scope information available.",
        "HISTORICAL_HOT_SPOTS": hot_spots or "No historical data available.",
    })

    await run_agent(prompt, config, cwd=config.target)

    # Validate + collect all AU-*.json files from result_dir
    au_files = sorted(glob(os.path.join(result_dir, "AU-*.json")))
    # Validate each file (reuse stage 3 validator logic)
    # Parse into list[AnalysisUnit]
    return analysis_units
```

Key differences from current:
- Output is a directory of AU files, not a single JSON.
- Returns `list[AnalysisUnit]` directly (what stage 3 used to return).
- The `AnalysisUnit` objects get `id`, `au_file_path`, `project_root` populated by the runner (same as current stage 3 renumbering, but no `module_id` needed).
- Only AUs with `analyze: true` are returned for downstream processing. The stage runner reads the directive, extracts the two sections via `parse_auditing_focus()`, and filters AUs accordingly.

### 3. Delete `stages/stage3.py`

No longer needed. All its logic (parallel per-module agents, renumbering, collect) is eliminated.

### 4. Parsing: rewrite `parsing/stage2.py`, delete `parsing/stage3.py`

New `parsing/stage2.py`:

```python
def parse_au_files(result_dir: str, only_analyze: bool = True) -> list[AnalysisUnit]:
    """Read all AU-*.json files and return AnalysisUnit list."""
    # For each AU-{N}.json:
    #   parse JSON → extract description, files, focus, analyze
    #   if only_analyze and not analyze: skip
    #   construct AnalysisUnit(id="AU-{N}", au_file_path=..., project_root=...)
```

Also add `parse_auditing_focus(path) -> tuple[str, str]` that reads the stage 1 auditing focus file and extracts the two section bodies (scope modules, historical hot spots) by splitting on the markdown headings.

Delete `parsing/stage3.py` — its `parse_au_file()` logic gets absorbed into the new `parsing/stage2.py`.

### 5. Validation: rewrite `validation/stage2.py`, delete `validation/stage3.py`

New `validation/stage2.py` validates the **directory of AU files**:

- At least one `AU-*.json` file exists.
- Each file passes the current stage 3 per-file checks:
  - Valid JSON
  - Has non-empty `description` (no placeholders)
  - Has non-empty `files` array
  - Has non-empty `focus` (no placeholders)
  - Has boolean `analyze` field
- IDs are sequential (`AU-1`, `AU-2`, ...) based on filenames.
- No more than 50 units have `analyze: true`.

Delete `validation/stage3.py`.

### 6. Orchestrator: update `orchestrator.py`

Remove stage 3 call. The handoff becomes:

```python
# Stage 1 produces auditing_focus_path (unchanged)

# Stage 2: Decompose into analysis units (merged, now receives auditing focus)
analysis_units = await run_stage2(config, checkpoint, auditing_focus_path)

# Stage 4: Bug discovery per AU (unchanged, still receives auditing focus)
findings = await run_stage4(analysis_units, config, checkpoint, auditing_focus_path, ...)
```

Update stage numbering in logging/UI. Two options:

- **Option A (recommended):** Keep the stage numbers as-is but skip 3. Stage 2 now produces AUs. Stages 4/5/6 keep their numbers. Simple, no downstream renumbering needed.
- **Option B:** Renumber everything (2→2, old4→3, old5→4, old6→5). More churn, breaks `--skip-stages` muscle memory.

Recommend **Option A** for minimal diff.

### 7. Checkpoint: update keys

- Current: `"stage2"` marks module decomposition done; `"stage3:{module_id}"` marks per-module AU splitting done.
- New: `"stage2"` marks the merged decomposition done. Remove all `"stage3:*"` checkpoint handling.
- Stage 4+ checkpoint keys unchanged.

### 8. `AnalysisUnit` dataclass: drop `module_id`

Currently `AnalysisUnit` has `module_id` to trace back to the source module. Since there are no modules anymore, drop this field. Check if stage 4/5/6 or the report uses `module_id` — if so, remove those references.

Alternatively, if we want to preserve some grouping info in the report, we could add an optional `group` or `category` field to the AU JSON, but this is not essential.

### 9. Output directory layout

Current:
```
stage-2-modules.json
stage-3-details/
  AU-1.json
  AU-2.json
  ...
```

New:
```
stage-2-details/
  project-summary.json
  AU-1.json
  AU-2.json
  ...
```

Update any hardcoded paths in stage 4 or report generation that reference `stage-3-details/`.

### 10. `--skip-stages` flag

Currently `--skip-stages 2` skips module decomposition and `3` skips AU splitting. After the merge:
- `2` skips the merged decomposition.
- `3` becomes a no-op (or we can remove it from the valid set / log a warning).
- Other stage numbers unchanged.

### 11. Delete prompt: `prompts/stage3.md`

No longer needed.

### 12. Tests: update `tests/test_parsers_and_report.py`

- Remove stage 3 parser/validator tests.
- Update stage 2 parser tests to match new AU-file output format.
- Add validation tests for the new directory-of-AU-files validator.

---

## Files to modify

| File | Action |
|------|--------|
| `prompts/stage2.md` | Rewrite — merge stage 2 + 3 prompt guidance |
| `prompts/stage3.md` | Delete |
| `code_auditor/stages/stage2.py` | Rewrite — produce AU files directly |
| `code_auditor/stages/stage3.py` | Delete |
| `code_auditor/parsing/stage2.py` | Rewrite — parse AU files from directory |
| `code_auditor/parsing/stage3.py` | Delete |
| `code_auditor/validation/stage2.py` | Rewrite — validate directory of AU files |
| `code_auditor/validation/stage3.py` | Delete |
| `code_auditor/orchestrator.py` | Remove stage 3 call, wire stage 2 → stage 4, pass `auditing_focus_path` to stage 2 |
| `code_auditor/config.py` | Remove `module_id` from AnalysisUnit if present |
| `code_auditor/checkpoint.py` | Remove stage 3 checkpoint keys |
| `code_auditor/report/generate.py` | Remove module_id references if any |
| `code_auditor/tests/test_parsers_and_report.py` | Update tests |

---

## Risk / tradeoffs

**Upside:**
- Halves context window usage for decomposition (one pass instead of two).
- Removes N parallel agent calls (stage 3 had one agent per module).
- Simpler data flow — no intermediate module abstraction.
- Fewer moving parts: less parsing, validation, checkpointing code.

**Downside:**
- The single decomposition agent must reason about granularity while also understanding the full codebase. Current stage 3 agents can focus on one module at a time with its full file listing in context.
- For very large projects (thousands of files), the single agent may struggle to produce correctly-sized AUs in one pass. Mitigation: the validation + retry loop catches this, and we can add a LOC heuristic in the prompt.
- Loss of `module_id` grouping in the report (minor — AUs are still named descriptively).

**Judgment:** The tradeoff is worth it. The current stage 3 agents mostly rubber-stamp small modules as single AUs anyway; the splitting logic only fires for large modules. Baking the size constraint into the initial decomposition is more efficient.
