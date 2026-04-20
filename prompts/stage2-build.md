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
