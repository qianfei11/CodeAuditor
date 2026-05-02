# Enable Timeout CLI Design

## Purpose

Invert the current timeout CLI behavior. CodeAuditor should run without per-stage agent timeouts by default, and users should opt in to the existing timeout with `--enable-timeout`.

## Current Behavior

- `--disable-timeout` is accepted by the CLI.
- Without the flag, the CLI sets `agent_timeout_seconds` to `DEFAULT_AGENT_TIMEOUT_SECONDS`.
- With the flag, the CLI sets `agent_timeout_seconds` to `None`.

## Target Behavior

- `--enable-timeout` is accepted by the CLI.
- Without the flag, the CLI sets `agent_timeout_seconds` to `None`.
- With the flag, the CLI sets `agent_timeout_seconds` to `DEFAULT_AGENT_TIMEOUT_SECONDS`.
- `--disable-timeout` is no longer accepted.

## Implementation

- Update `code_auditor/__main__.py` to register `--enable-timeout` with `argparse`.
- Map `args.enable_timeout` to `agent_timeout_seconds` in `main()`.
- Keep `DEFAULT_AGENT_TIMEOUT_SECONDS` in `code_auditor/config.py` as the single timeout duration source.
- Keep the lower-stage behavior unchanged: stages 5 and 6 already treat `None` as disabled timeout and an integer as enabled timeout.

## Documentation

- Update `README.md` common options to document `--enable-timeout` and the no-timeout default.
- Update `CLAUDE.md` quick reference to document the same behavior.

## Tests

- Update CLI parser tests to accept `--enable-timeout`.
- Add or update main mapping tests so the default config has `agent_timeout_seconds is None`.
- Add or update main mapping tests so `--enable-timeout` maps to `DEFAULT_AGENT_TIMEOUT_SECONDS`.
- Update rejection tests so `--disable-timeout` is rejected.
