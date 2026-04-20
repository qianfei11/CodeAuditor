# Deployment Realization Stage — Follow-ups

Issues surfaced by the final code review for the `feature/deployment-realization` branch (commits `5d1cbc9..e1b299e`). These are **deviations from the plan's verbatim code that the implementation faithfully shipped**, so they are deferred to a follow-up PR rather than retrofitted into this branch.

Implementation reference: `docs/superpowers/plans/2026-04-20-deployment-realization-stage.md`.
Spec reference: `docs/superpowers/specs/2026-04-19-deployment-realization-stage-design.md`.

## Important — defensive handling around partial Stage 2 state

These four items share a theme: graceful handling of edge cases where Stage 2 ran partially, was skipped, or its outputs were manually disturbed.

### I-1: Phase A repair prompt loses original schema context

**Where:** `code_auditor/stages/stage2_deployments.py:191-199` inside `_run_phase_a`.

**Problem:** When Phase A's output fails `validate_stage2_phase_a`, the runner sends a repair prompt containing only the validation issues. Each `claude-code-sdk` invocation launches a fresh agent subprocess — the previous turn's prompt context is gone. The repair agent will see "fix these issues" without knowing the manifest schema, the `__CONFIGS_DIR__` location, the `kebab-case` id rule, or the rule that build fields must be null.

Stage 3 has the same pattern but works because its validation issues themselves embed enough context (file paths, expected fields). Phase A's issues do reference paths but not the schema.

**Fix idea:** include the original Phase A prompt body (or a condensed schema reminder) in the repair prompt. Or have the repair prompt explicitly tell the agent to re-read the manifest at `__MANIFEST_PATH__` and the schema spec from `prompts/stage2.md`.

### I-2: Phase B crashes if `manifest.json` is missing but `stage2:research` marker is present

**Where:** `code_auditor/stages/stage2_deployments.py:307` (`_run_phase_b` calls `_load_manifest` unconditionally).

**Problem:** If a user deletes `output_dir/stage2-deployments/manifest.json` manually but leaves the `.markers/stage2-research` checkpoint marker in place, `_run_phase_a` skips on the resume path, `_run_phase_b` then immediately attempts `_load_manifest` and raises `FileNotFoundError`. The whole Stage 2 run aborts ungracefully.

The spec (§2.5) says: "If Phase A is re-run (marker deleted) and produces a different set of archetype IDs, stale `configs/<id>/` directories from the previous run are not auto-deleted — the runner logs a warning naming them." This warning is also not implemented.

**Fix idea:** in `_run_phase_a`, treat "marker present + manifest missing" as needing a re-run (or fail loudly with a clear message). Add the stale-configs warning while in the area.

### I-3: Phase B agent exceptions silently swallowed

**Where:** `code_auditor/stages/stage2_deployments.py:289-291` (`_run_one_build` re-raises) and `_run_phase_b` (lines ~318-321) discards `run_parallel_limited`'s return value.

**Problem:** When a Phase B agent crashes (claude-code-sdk error, OOM, network fault, etc.), `_run_one_build` re-raises. `run_parallel_limited` catches and stores `("rejected", None, exc)`. `_run_phase_b` ignores the result tuple. The merge step then sees no `result.json` and downgrades to `infeasible` with reason `"result.json missing — Phase B did not produce an outcome."` — losing the actual exception type/message and failing to preserve the agent log.

The plan's choice is robust but informationally lossy. Compare to Stage 4's pattern at lines 108-113 which logs per-finding rejections.

**Fix idea (option A):** in `_run_phase_b`, after `run_parallel_limited`, iterate the results and log per-build rejections.

**Fix idea (option B):** generalize `_write_timeout_result` → `_write_failure_result(status, reason, ...)`. In `_run_one_build`'s `except Exception` branch, log the type+message, write a synthetic crash result.json, copy build.log to `cfg_dir`, then `mark_complete`. This makes Phase B's contract uniformly "every config gets a result.json with a non-vacuous reason".

### I-5: Stage 6 prompt receives non-existent manifest path when Stage 2 is skipped

**Where:** `code_auditor/orchestrator.py` Stage 6 wiring (passes `deployment_manifest_path` always); `prompts/stage6.md` Step 0 ("Read `__DEPLOYMENT_MANIFEST_PATH__`...").

**Problem:** If `skip_stages` includes `2` on a fresh output dir, `deployment_manifest_path` resolves to the default `os.path.join(deployments_dir, "manifest.json")`, which doesn't exist. Stage 6's Step 0 tells the agent to read the file. The prompt's fallback ("If no entry has `build_status == \"ok\"`, fall back to building from source") doesn't anticipate "manifest doesn't exist at all".

**Fix idea:** orchestrator detects the missing manifest before Stage 6 and passes a sentinel path / empty manifest, OR Step 0 in the prompt explicitly handles "no manifest file" as identical to "no entry has `ok`".

---

## Important — type semantics

### I-4: `validate_stage2_manifest_final` mixes warning/error semantics in one return type

**Where:** `code_auditor/validation/stage2.py` `validate_stage2_manifest_final`.

**Problem:** Returns `list[ValidationIssue]` — same type as hard validators — but its docstring says "Returns warnings... the runner should not abort on these." The runner loop at `stage2_deployments.py:341-342` does just log, so behavior is correct, but mixing semantics in one type may confuse future contributors.

**Fix idea:** rename to `get_manifest_final_warnings` / `manifest_final_warnings` to clarify, OR add a `severity: Literal["warning", "error"] = "error"` field to `ValidationIssue` (touches all validators).

---

## Minor — observability / cleanup

### M-1. `Stage2Output.deployment_summary_path` not file-existence-checked
`load_stage2_output` blindly joins paths. Stages 3/4 guard with `os.path.exists` so harmless in practice; could log when the path is dead.

### M-2. Stylistic mix of `entry.setdefault(...)` and `entry["x"] = ...` in `merge_results_into_manifest`
Lines 94-95 use `setdefault`; neighboring lines unconditional assignment. Stylistic only.

### M-3. Test function names are stale after the renumber
`test_stage2_parser_reads_au_files`, `test_stage2_validator_*`, `test_stage4_validator_*` (which actually tests Stage 5's validator). Cosmetic but confusing.

Also: `stages/stage5.py` has local variables named `stage3_file_path`, `stage3_filename`, `stage4_dir` (whose value points at `stage5-vulnerabilities/`); `stages/stage7.py` has `stage6_vuln_dir` (value points at `stage7-disclosures/`). Per-plan deferral; could rename in this follow-up.

### M-4. Phase A prompt has unused `__DEPLOYMENTS_DIR__` substitution
Dict at `stage2_deployments.py:166-174` includes `deployments_dir` but `prompts/stage2.md` never references `__DEPLOYMENTS_DIR__`. Harmless; remove the dict key or use it in the prompt.

### M-5. Phase B prompt's "race detector" example for Go is misleading
Line 21 of `prompts/stage2-build.md` lists "race detector for Go" as a sanitizer. Race detector finds data races, not memory-safety issues — for a security audit looking at memory safety this is inaccurate guidance. Replace with "Go: `-race` for concurrency bugs; for memory issues, no native sanitizer (acceptable to ship without one)."

### M-6. `fp_report_path` in `stages/stage6.py:54` is computed before the resume guard
Variable defined at function top before the early-return checkpoint check. Cosmetic; doesn't affect correctness.

### M-7. `validate_stage2_phase_a` does not enforce id-matches-deployment-mode-path
Phase A validator accepts `id: foo` with `deployment_mode_path: configs/bar/deployment-mode.md` as long as the file at `bar` exists. Phase B's per-entry validator does enforce id match against the dir basename, so the inconsistency surfaces later — but Phase A could catch it earlier with a one-line check.

### M-8. `stage2-deployments/configs/` is created three times
- `stages/stage0.py:58` (during setup)
- `_run_phase_a` (line 158) inside `os.makedirs(...exist_ok=True)`
- `run_stage2_deployments` (line 331)

All idempotent thanks to `exist_ok=True`, harmless.

### M-9. Repo-root `CLAUDE.md` is stale
`/home/audit/code_auditor/CodeAuditor/CLAUDE.md` (the parent worktree) still describes the old 7-stage pipeline + removed flags. Will pick up the changes on merge of this branch into `main`. Worth a sanity check after merge.

---

## Out of scope (do not address in this follow-up)

- The pre-existing 4-line stub at `parsing/stage3.py` was correctly `git rm`-ed during the renumber (commit `5d1cbc9`). Implementer note in T2 was about an inconsistency in the rename phrasing, not a real loss of functionality.
- Lint/PEP 8 import-not-at-top observations in test file. No lint configured in this project (`pyproject.toml` has no ruff/flake8 config), so cosmetic at best.
- "Three-flavor build" (production + instrumented variants) — explicitly out of scope per the spec ("Instrumented only" decision).
