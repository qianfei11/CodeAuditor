# Deployment Realization Stage — Design

## Problem statement

CodeAuditor's pipeline has no concept of *how the target is actually deployed in the real world*. As a result (using today's stage numbers):

- Stage 2 (AU decomposition) and Stage 3 (bug discovery) treat all modules equally; bugs in code that never runs in production are weighed the same as bugs on the externally exposed surface.
- Stage 4 (evaluation) and Stage 5 (PoC) reason about "default configuration" and "real-world reachability" as a pure-LLM judgment — there is no executable ground truth to test claims against.
- Stage 5 (PoC) builds the target ad-hoc per finding, repeating build work and producing inconsistent build environments across findings.

The goal is to make real-world deployment a first-class artifact in the pipeline: pre-build the target as it actually runs in production, then exploit-test against that running deployment so the "is this real-world reachable?" question is answered empirically.

## Decisions

- **Insert a new Stage 2 — Deployment Realization** between current Stage 1 and current Stage 2. All later stages renumber up by one. No backward compatibility for existing `output_dir/` layouts; existing audits do not resume cleanly across this change.
- **Two-phase internal structure for Stage 2:**
  - **Phase A (research):** a single agent investigates how the project is run in production and identifies 1–N deployment archetypes. Output is conceptual only — a deployment-mode description per archetype, no build commands.
  - **Phase B (realization):** one agent per archetype, run in parallel up to a new `deployment_build_parallel` cap. Each agent figures out how to build the target into the chosen archetype, executes the build (instrumented with sanitizers/debug symbols), validates with a smoke test, and reports outcome.
- **Pre-built artifacts only — not running deployments.** Phase B produces launchable artifacts (binaries, container images). Stage 6 (PoC) launches them on demand.
- **Instrumented builds only.** Phase B produces sanitizer-instrumented builds (ASAN/UBSAN/etc., language-appropriate) so Stage 6 captures high-quality evidence without rebuilding. The deployment topology, configuration options, and exposed interfaces match real-world production; only the compile flags add instrumentation.
- **LLM-driven config selection in Stage 6.** The PoC agent reads the deployment manifest and picks the best-fitting config per finding.
- **Deployment summary feeds Stages 3, 4, and 6** as an additive prompt input. Stage 5 (evaluation) is unchanged — empirical reachability testing happens in Stage 6 against the live deployment.
- **Phase B retry policy:** each build agent gets a generous turn budget (`max_turns=500`, mirroring today's PoC stage) and iterates until it either succeeds or concludes the deployment is **infeasible in the current environment**. A wall-clock timeout (default 30 min) backs the budget. Three terminal outcomes: `ok`, `infeasible`, `timeout`.
- **Skip-and-continue on build failure.** Failed configs are excluded from the manifest's usable set; the pipeline continues with surviving configs. If zero configs build successfully, Stage 6 falls back to today's behavior (ad-hoc build per finding) with a logged warning.
- **New CLI flag `--deployment-build-parallel`** (default `1`) — separate from `--max-parallel`, since builds are CPU/RAM heavy while existing static-analysis agents are network-bound.

## Pipeline shape

| # | Stage | Parallelism |
|---|-------|-------------|
| 0 | Setup (was 0) | none |
| 1 | Security context research (was 1) | single |
| **2** | **Deployment Realization (NEW)** | **single research agent + N parallel build agents (capped by `deployment_build_parallel`)** |
| 3 | AU decomposition (was 2) | single |
| 4 | Bug discovery (was 3) | per AU |
| 5 | Evaluation (was 4) | per finding |
| 6 | PoC reproduction (was 5) | per vuln |
| 7 | Disclosure (was 6) | per vuln |

## Change 1: New CLI flag and config

**`code_auditor/config.py`** — add to `AuditConfig`:

```python
deployment_build_parallel: int = 1
deployment_build_timeout_sec: int = 1800   # 30 min wall-clock per build agent
```

**`code_auditor/__main__.py`** — add CLI flag:

```python
parser.add_argument(
    "--deployment-build-parallel",
    type=int,
    default=1,
    help="Maximum concurrent deployment build agents in stage 2 (default: 1). "
         "Separate from --max-parallel because builds are CPU/RAM heavy.",
)
```

Wire `args.deployment_build_parallel` into the `AuditConfig` constructor.

`--max-parallel` semantics are unchanged and apply to stages 4/5/6/7 as today.

## Change 2: New Stage 2 — Deployment Realization

### 2.1 Output layout

```
output_dir/stage2-deployments/
├── manifest.json                       # archetypes (Phase A) + build outcomes (Phase B)
├── deployment-summary.md               # short directive injected into stages 3/4/6
├── configs/
│   └── <config-id>/
│       ├── deployment-mode.md          # Phase A: role, exposed surface, behavior contract
│       ├── result.json                 # Phase B: per-config outcome
│       ├── build.sh                    # Phase B (agent-authored)
│       ├── launch.sh                   # Phase B (agent-authored)
│       ├── smoke-test.sh               # Phase B (validates Phase A behavior contract)
│       ├── build.log                   # Phase B agent log
│       └── <build artifacts>           # binaries, images, etc.
└── agent.log                           # Phase A research agent log
```

### 2.2 Phase A — research agent (single, sequential)

**Inputs:** `auditing-focus.md` from Stage 1, `stage-1-security-context.json` (its `deployment_model` field is currently underused — Phase A consumes it).

**Task:** investigate how the project is actually deployed in production by reading project docs, examples, upstream Dockerfiles, distro packaging defaults. Identify 1–N **deployment archetypes** that materially differ in attack surface. For each archetype, produce a conceptual description only — no build commands, no compile flags, no scripts.

**Output:**

- `deployment-summary.md`: one paragraph per archetype (role + exposed surface + modules exercised), suitable for injection into downstream prompts.
- `manifest.json` (build fields all `null` after Phase A):

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

- `configs/<id>/deployment-mode.md`: free-form narrative covering the role the target plays in this archetype, the network/IPC surface it exposes, the kinds of inputs it processes, and a behavioral contract (the smoke test in Phase B will exercise this contract).

**Prompt requirements (drives Phase A `prompts/stage2.md`):**

- Each archetype must be grounded in evidence from docs, examples, or distro packaging found during research. The agent must not invent archetypes the project does not actually support.
- IDs are kebab-case and unique within the manifest.
- `exposed_surface` and `modules_exercised` must be non-empty.
- The agent must not write `build.sh`, `launch.sh`, or `smoke-test.sh` — those are Phase B's job.

**Agent settings:** `max_turns=200`, model `config.model` (default `claude-sonnet-4-6`).

**Checkpoint key:** `stage2:research`.

### 2.3 Phase B — per-config build agents (parallel)

**Trigger:** one agent per entry in `manifest.json`'s `configs` array, run via `run_parallel_limited` with concurrency capped at `config.deployment_build_parallel`.

**Per-agent inputs:** the archetype's `deployment-mode.md`, the target source path, the per-config working directory `configs/<id>/`.

**Task:** realize the deployment mode as a runnable instrumented build.

1. Decide the build approach (compile flags, configure options, container or bare-metal) consistent with the archetype's behavior contract.
2. Author `build.sh` and `launch.sh`. Add sanitizer/debug instrumentation appropriate for the language and build system.
3. Execute `build.sh`. Iterate on failures (install missing dependencies, adjust flags, debug build errors) within the turn and time budget.
4. Author `smoke-test.sh` exercising the behavior contract from `deployment-mode.md`. Launch the artifact, run the smoke test.
5. Write `configs/<id>/result.json` with the terminal outcome.

**Iteration policy:** the agent retries within its own turn budget until it either succeeds or concludes the deployment is infeasible in the current environment. The runner does not impose a retry counter. Examples of valid `infeasible` reasons:

- Missing system dependency that cannot be installed in this environment.
- Requires hardware/kernel features not present (specific NICs, eBPF, RDMA, etc.).
- Requires proprietary or licensed components unavailable.
- Upstream build system broken at this revision and not patchable without source modification.

**Wall-clock timeout:** `config.deployment_build_timeout_sec` (default `1800`). On expiry, the runner cancels the agent and writes `result.json` with `build_status: "timeout"` if the agent did not write its own.

**`result.json` schema:**

```json
{
  "id": "httpd-static-tls",
  "build_status": "ok | infeasible | timeout",
  "artifact_path": "absolute path to launchable artifact, or null",
  "launch_cmd": "shell command (or path to launch.sh), or null",
  "build_failure_reason": "specific load-bearing reason, or null",
  "attempts_summary": "short summary of approaches tried, or null"
}
```

For `build_status == "ok"`: `artifact_path`, `launch_cmd` non-null; `build_failure_reason` null.
For `build_status ∈ {"infeasible", "timeout"}`: `build_failure_reason` and `attempts_summary` non-null and specific (the validator rejects vacuous strings like "build failed" or "unknown error").

**Agent settings:** `max_turns=500`, model `claude-opus-4-6`, `effort=medium` (mirrors existing PoC stage — build problem-solving benefits from the stronger model).

**Checkpoint key per agent:** `stage2:build:<config-id>`. Marker is set after the agent terminates regardless of outcome (success or `infeasible`/`timeout` is captured in `result.json`).

### 2.4 Manifest merge and final validation

After all Phase B agents terminate, the runner merges each `configs/<id>/result.json` into the corresponding `manifest.json` entry, then runs the final manifest validator. If a `result.json` is missing or fails validation, the runner downgrades that entry to `build_status: "infeasible"` with `build_failure_reason: "result.json failed validation: <issues>"` so downstream stages see consistent semantics.

If zero entries end up with `build_status == "ok"`, the runner logs a warning. The pipeline continues; Stage 6 will fall back to ad-hoc building.

### 2.5 Resume semantics

- `stage2:research` complete and `manifest.json` exists → skip Phase A, load archetypes from manifest.
- For each archetype, `stage2:build:<id>` complete → skip that build agent. The runner re-merges all `result.json` files every run so re-running after editing one config still produces a fresh `manifest.json`.
- Deleting a `configs/<id>/` directory and its marker triggers a re-build of just that config on next run.
- If Phase A is re-run (marker deleted) and produces a different set of archetype IDs, stale `configs/<id>/` directories from the previous run are not auto-deleted — the runner logs a warning naming them. Cleanup is a user action; auto-deletion would be too aggressive given the cost of rebuilds.

## Change 3: Validation

New file `code_auditor/validation/stage2.py` exposing three functions, all returning `list[ValidationIssue]`:

### `validate_stage2_phase_a(deployments_dir: str)`

Runs after the Phase A agent finishes, before Phase B starts. Checks:

- `manifest.json` exists and parses as JSON with a `configs: []` array.
- `configs` has length ≥ 1.
- Each entry has non-empty `id` (kebab-case, unique within the manifest), `name`, `deployment_mode_path`, `exposed_surface` (non-empty list), `modules_exercised` (non-empty list).
- Each `deployment_mode_path` resolves to an existing non-empty file under `configs/<id>/deployment-mode.md`.
- `deployment-summary.md` exists at the expected path and is non-empty.
- Build fields (`build_status`, `artifact_path`, `launch_cmd`, `build_failure_reason`, `attempts_summary`) are all `null`.

On validation failure, the runner uses the same one-shot repair prompt pattern as today's Stage 2 (current `stages/stage2.py` lines 86–99): hand the agent the issues and ask it to fix. Single repair attempt; if it still fails, log warnings and proceed.

### `validate_stage2_phase_b_entry(config_dir: str)`

Runs per-config after each build agent finishes, against `configs/<id>/result.json`. Checks:

- `result.json` exists with `id` matching the directory name and `build_status ∈ {"ok", "infeasible", "timeout"}`.
- If `build_status == "ok"`: `artifact_path` and `launch_cmd` non-empty; `artifact_path` exists on disk; `build.sh`, `launch.sh`, `smoke-test.sh` exist and are executable.
- If `build_status ∈ {"infeasible", "timeout"}`: `build_failure_reason` non-empty and not in a small denylist of vacuous strings (`"build failed"`, `"unknown error"`, `"failed"`, `"error"`); `attempts_summary` non-empty.

No repair loop. Malformed entries are downgraded by the runner per Section 2.4.

### `validate_stage2_manifest_final(manifest_path: str)`

Runs after the merge step. Checks:

- All Phase A entries are present (no losses during merge).
- At least one entry has `build_status == "ok"` (warning, not error — the pipeline continues).

## Change 4: Downstream prompt changes

The deployment summary written by Phase A is injected as a new placeholder into stages 3, 4, and 6.

### Stage 3 (AU decomposition, `prompts/stage3.md` after renumber)

Add `__DEPLOYMENT_SUMMARY__` placeholder rendered alongside existing `__SCOPE_MODULES__` and `__HISTORICAL_HOT_SPOTS__`. New section:

> ## Real-World Deployment Surfaces
>
> The following deployment archetypes were identified for this project. When decomposing into analysis units, prioritize modules that are exercised in these deployments and on the externally exposed surface. Modules unreachable in any of these archetypes can be deprioritized or grouped into lower-priority AUs.
>
> __DEPLOYMENT_SUMMARY__

This is additive — it biases AU selection toward what runs in production without removing existing focus signals.

### Stage 4 (bug discovery, `prompts/stage4.md`)

Add a similar block:

> ## Real-World Reachability Context
>
> The deployment archetypes below describe how this code is run in production. When evaluating a candidate bug, prefer ones reachable from these deployment entry points. A bug only reachable from code that runs in no archetype is lower-confidence.
>
> __DEPLOYMENT_SUMMARY__

This is guidance, not a hard filter. Stage 4 still emits findings; the actual filter is the Stage 6 PoC against the live deployment.

### Stage 6 (PoC reproduction, `prompts/stage6.md`)

Two changes.

**Add Step 0 — Select a Pre-Built Deployment** (before today's Step 1). New input placeholders: `__DEPLOYMENT_MANIFEST_PATH__`, `__DEPLOYMENTS_DIR__`.

> ### Step 0: Select a Pre-Built Deployment
>
> Read `__DEPLOYMENT_MANIFEST_PATH__`. From entries with `build_status == "ok"`, pick the single config whose `exposed_surface` and `modules_exercised` best match this finding's location and trigger. State your choice and one-sentence reasoning. Use the config's `launch_cmd` to start the artifact under `__POC_DIR__`. Do not rebuild — the artifact is already instrumented.
>
> If no entry has `build_status == "ok"`, fall back to building from source per the original instructions and note this in the report.

**Drop Step 4 — Real-World Exploitability Assessment** (today's lines 116–128 in `prompts/stage5.md`). The judgment it asks the LLM to make about default-config plausibility is now executed empirically by attacking the pre-built deployment. Keep `Reproduction Status: false-positive` as the outcome label when the PoC cannot trigger against the chosen deployment — that semantics is unchanged.

### Stages unchanged

0, 1, 5 (evaluation), 7 (disclosure). Stage 5 keeps its data-flow trace + CVSS reasoning as-is; deployment context isn't load-bearing there since reachability under real deployments is now Stage 6's empirical job.

## Change 5: Orchestrator wiring

`code_auditor/orchestrator.py` inserts the new stage call between current stage 1 and current stage 2 (renumbered to stage 3), and threads the new paths into stages 3, 4, and 6.

```python
from .stages.stage2_deployments import Stage2Output, run_stage2_deployments

# ... stage 1 unchanged ...

# Stage 2: deployment realization
stage2_out: Stage2Output | None = None
if 2 not in config.skip_stages:
    stage2_out = await run_stage2_deployments(
        config, checkpoint, auditing_focus_path,
    )

deployments_dir = os.path.join(config.output_dir, "stage2-deployments")
deployment_summary_path = (
    stage2_out.deployment_summary_path if stage2_out
    else os.path.join(deployments_dir, "deployment-summary.md")
)
deployment_manifest_path = (
    stage2_out.manifest_path if stage2_out
    else os.path.join(deployments_dir, "manifest.json")
)

# Stage 3 (was stage 2): AU decomposition — also takes deployment_summary_path
analysis_units = await run_stage3_decompose(
    config, checkpoint, auditing_focus_path, deployment_summary_path,
)
# Stage 4 (was 3): bug discovery — takes both directives + deployment summary
# Stage 5 (was 4): evaluation — unchanged signature
# Stage 6 (was 5): PoC — takes deployment_manifest_path and deployments_dir
# Stage 7 (was 6): disclosure — unchanged
```

The `skip_stages` field stays in `AuditConfig` for internal use even though the user-facing CLI flag for it is gone (per current `__main__.py`). Same pattern as today.

`Stage2Output` dataclass:

```python
@dataclass
class Stage2Output:
    manifest_path: str
    deployment_summary_path: str
    configs: list[DeploymentConfig]   # only entries with build_status == "ok"
```

## Change 6: Output paths and renumbering

### Renames in `output_dir/`

| Old path | New path |
|----------|----------|
| `stage1-security-context/` | `stage1-security-context/` (unchanged) |
| — | `stage2-deployments/` (new) |
| `stage2-analysis-units/` | `stage3-analysis-units/` |
| `stage3-findings/` | `stage4-findings/` |
| `stage4-vulnerabilities/` | `stage5-vulnerabilities/` |
| `stage5-pocs/` | `stage6-pocs/` |
| `stage6-disclosures/` | `stage7-disclosures/` |

### Code renames in `code_auditor/`

| Old | New |
|-----|-----|
| `stages/stage2.py` | `stages/stage3.py` |
| `stages/stage3.py` | `stages/stage4.py` |
| `stages/stage4.py` | `stages/stage5.py` |
| `stages/stage5.py` | `stages/stage6.py` |
| `stages/stage6.py` | `stages/stage7.py` |
| `validation/stage2.py` … `stage6.py` | `validation/stage3.py` … `stage7.py` |
| `parsing/stage2.py` | `parsing/stage3.py` |
| `prompts/stage2.md` … `stage6.md` | `prompts/stage3.md` … `stage7.md` |

### New files

- `code_auditor/stages/stage2_deployments.py`
- `code_auditor/validation/stage2.py`
- `prompts/stage2.md`

Internal `_TASK_KEY` constants in each renumbered stage file get updated (`"stage2"` → `"stage3"`, etc.). All cross-stage imports in `orchestrator.py` get updated. Logger names (`get_logger("stage2")` → `get_logger("stage3")`, etc.) get updated.

### No backward compat for old paths

Checkpoint markers from previous runs are stage-keyed; mixing old and new stage numbers in a half-resumed audit would be inconsistent. New runs start clean. README and CLAUDE.md gain a one-line note.

## Change 7: Tests

`code_auditor/tests/test_parsers_and_report.py` references stage-numbered functions and fixtures; these get renamed in lockstep.

New tests covering:

- Phase A manifest validation (happy path, missing fields, non-empty constraints, ID uniqueness, `deployment_mode_path` resolution).
- Phase B `result.json` validation (each `build_status` outcome, vacuous-reason denylist, missing-artifact detection for `ok`).
- Manifest merge correctness, including the missing/malformed `result.json` downgrade behavior.
- `--deployment-build-parallel` flag default and override.

No new tests make agent calls — same convention as today.

## Defaults

| Setting | Default | Rationale |
|---------|---------|-----------|
| `deployment_build_parallel` | `1` | Builds are CPU/RAM heavy; user opts into more. |
| `deployment_build_timeout_sec` | `1800` (30 min) | Mirrors existing Stage 5/6 PoC wall-clock pattern. |
| Phase A `max_turns` | 200 | Matches existing Stage 1. |
| Phase B `max_turns` | 500 | Matches existing PoC stage — agents iterate until success or infeasibility. |
| Phase A model | `config.model` (default `claude-sonnet-4-6`) | Research workload; default model suffices. |
| Phase B model | `claude-opus-4-6`, `effort=medium` | Build problem-solving benefits from stronger model; same rationale as existing PoC stage. |

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Pre-built artifacts consume large disk (multiple instrumented builds of large projects). | Documented in README. Per-config `result.json` lets users delete individual config dirs to free space and resume the rest. |
| Phase A agent invents archetypes the project does not actually support. | Validator requires non-empty `modules_exercised`. Phase B will fail to build a fictional archetype, downgrading it to `infeasible`. The system self-corrects, but at compute cost. Phase A prompt explicitly requires each archetype be grounded in evidence found during research. |
| Phase B build agent gets stuck installing system dependencies and exhausts the 30-min timeout on a buildable target. | `deployment_build_timeout_sec` is configurable; users can raise it for known-slow targets. Timeout is logged with full agent log preserved for diagnosis. |
| Stage 6's deployment selection picks the wrong config and wastes the per-finding time budget on a false negative. | Stage 6 fallback path already exists (no `ok` config → ad-hoc build). On selection-but-no-trigger, today's `false-positive` outcome stands — same observable behavior as today. Automatic re-selection across configs is not implemented (would multiply per-finding cost); documented limitation. |
| Renumbering breaks any saved `output_dir/` from previous audits. | One-line README note: existing audit outputs are stage-numbered and will not resume cleanly; either finish them on the old code or start fresh. |
| Stale `configs/<id>/` dirs after Phase A re-run with different archetype IDs. | Runner logs warnings naming the stale dirs but does not delete (artifacts are expensive). User-driven cleanup. |

## Open knobs left to user discretion in the prompt, not the runner

- How many archetypes Phase A produces (1–N, agent decides per-target).
- Which sanitizers and instrumentation Phase B picks per language and build system.
- How aggressively Phase B installs system packages vs. concludes infeasibility (within the timeout).
