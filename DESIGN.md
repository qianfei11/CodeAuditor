# Plan: Agent SDK Application for Network Protocol Security Audit

## Context

The existing Claude Code skill (`audit-network-protocol/`) orchestrates a 5-stage security audit pipeline via sub-agents. The core problem: Stage 3 assigns an entire module (with multiple entry points) to a single sub-agent, which overflows its context window, degrading both analysis quality and output format compliance. The fix — splitting Stage 3 into per-entry-point sub-agents — requires orchestration complexity (parsing Stage 2 output, fine-grained fan-out, concurrency control, merging results) that exceeds what the skill framework can reliably express.

The solution: rewrite the orchestrator as a Python application using the `claude-code-sdk` package, where deterministic code handles parsing, routing, concurrency, checkpoint/resume, and validation, while Claude sub-agents focus purely on analysis.

## Decisions

- **SDK**: `claude-code-sdk` (wraps Claude Code CLI, provides built-in tools)
- **Stage 4**: Per-finding granularity (1 agent per finding, consistent with per-EP philosophy)
- **Resumability**: Checkpoint-based — track completed tasks in a state file, skip on restart

## Architecture Overview

```
protocol_auditor/
├── main.py                  # CLI entry point (argparse)
├── orchestrator.py          # Main pipeline controller
├── stages/
│   ├── stage0_setup.py      # Directory creation, config collection
│   ├── stage1_scope.py      # Orient and Scope — 1 agent
│   ├── stage2_entry_points.py  # Per-module entry point identification
│   ├── stage3_analysis.py   # Per-ENTRY-POINT vulnerability analysis (key change)
│   ├── stage4_evaluation.py # Per-finding evaluation (1 agent per finding)
│   └── stage5_report.py     # Report generation (calls existing Python script)
├── parsing/
│   ├── stage1_parser.py     # Parse stage-1-scope.md → list of Module
│   └── stage2_parser.py     # Parse M-{ID}.md → list of EntryPoint
├── prompts/
│   ├── stage1.md            # Adapted from agents/stage-1-orient-and-scope.md
│   ├── stage2.md            # Adapted from agents/stage-2-identify-entry-points.md
│   ├── stage3.md            # Per-EP version of stage-3-vulnerability-analysis.md
│   ├── stage4.md            # Adapted from agents/stage-4-vulnerability-evaluation.md
│   └── stage5.md            # Adapted from agents/stage-5-generate-report.md
├── agent_utils.py           # Agent spawning, validation-retry, concurrency
├── checkpoint.py            # Checkpoint state management
├── config.py                # Configuration dataclasses
└── reference/               # Symlink to existing checklists
```

## Key Design Decisions

### 1. Stage 3 Decomposition (The Core Change)

**Before (skill):** 1 sub-agent per module, analyzes all entry points
**After (SDK app):** 1 sub-agent per entry point

The orchestrator:
1. Parses Stage 2 output files with Python regex (deterministic, no LLM)
2. Extracts individual entry point blocks (EP-1, EP-2, etc.)
3. Spawns one agent per entry point, providing only:
   - Threat model (from Stage 1)
   - The single entry point's details (type, location, attacker data, hints)
   - The relevant source file paths (not the whole module)
   - The language-specific checklist
   - Output format specification
4. Each agent writes **one file per finding** to `{output_dir}/stage-3-details/`:
   - File naming: `M-{ID}-EP-{N}-F-{NN}.md` (e.g., `M-1-EP-3-F-01.md`, `M-1-EP-3-F-02.md`)
   - Each file is self-contained: includes the finding details **plus** source context
     (module name, EP type/location, attacker-controlled data, relevant source file paths)
     so the Stage 4 agent has everything it needs without reading other files.
   - If no findings for an EP, no files are written (zero files is valid).
5. **No merge or parsing step between Stage 3 and 4.** The orchestrator simply lists all
   `*.md` files in `stage-3-details/` and feeds each one directly to a Stage 4 agent.
   Each file already has full context.

### 2. Stage 4 Per-Finding

Each finding from Stage 3 gets its own evaluation agent. The orchestrator:
1. Lists all `*.md` files in `stage-3-details/` — each is one self-contained finding
2. Spawns one agent per finding. The agent:
   - Verifies the vulnerability exists (filters false positives)
   - Evaluates severity (CVSS score → Critical/High/Medium/Low)
   - Writes output to a **temp file** (e.g., `stage-4-details/_pending/{stage3_filename}`)
3. After all Stage 4 agents complete, the orchestrator:
   - Reads the severity from each evaluated finding's temp file
   - Filters out findings the agent marked as false positives or below-Medium
   - Assigns globally unique IDs based on confirmed severity (C-01, H-01, M-01, L-01)
   - Renames/moves each file to `stage-4-details/{ID}.md` (e.g., `C-01.md`)

ID assignment is a **post-evaluation deterministic step** — the agent never needs to know
the global ID during evaluation. The ID is injected into the file by the orchestrator after
renaming (simple text replacement of a placeholder, or prepend to the file).

### 3. Concurrency Control

`asyncio.Semaphore(max_parallel)` (default 4) caps concurrent agents. Fan-out stages (2, 3, 4) submit all tasks; semaphore gates execution.

### 4. Validation-Retry Loop

After each agent completes:
1. Run existing validation script via `subprocess.run()`
2. If fails → resume the agent's session with validation errors as new prompt
3. Up to 2 retries
4. Log all validation outcomes

Scripts to review, test, and fix before integration:
- `script/validate_stage1.py` — reviewed, logic is sound
- `script/validate_stage2.py` — reviewed, logic is sound
- `script/validate_stage3.py` — reviewed; currently validates files with multiple findings
  per file. Needs update: now each file contains exactly one finding. Simplify to validate
  a single-finding file (still check required fields and severity).
- `script/validate_stage4.py` — reviewed, logic is sound
- `script/generate_report.py` — **bug found**: `parse_finding_file()` does not strip
  markdown code fences (`` ```json ... ``` ``) from the JSON block before parsing, while
  `validate_stage4.py` does. If agents wrap JSON in fences (which is common), report
  generation will fail with `JSONDecodeError`. Fix: add the same fence-stripping logic
  from `validate_stage4.py` (lines 124-125).

All scripts will be:
1. Reviewed (done — see above)
2. Unit tested with sample inputs before integration
3. Fixed where bugs are found (generate_report.py fence stripping)

### 5. Checkpoint / Resume System

A JSON state file (`{output_dir}/.checkpoint.json`) tracks:

```json
{
  "stage": 3,
  "completed_tasks": {
    "stage1": true,
    "stage2:M-1": true,
    "stage2:M-2": true,
    "stage3:M-1:EP-1": true,
    "stage3:M-1:EP-2": false,
    "stage3:M-2:EP-1": false
  },
  "config": { ... }
}
```

On restart with `--resume`:
- Load checkpoint, skip completed tasks
- Re-parse already-written output files to reconstruct state
- Resume from first incomplete task

### 6. Agent SDK Usage Pattern

```python
from claude_code_sdk import query, ClaudeCodeOptions

async def run_analysis_agent(
    prompt: str,
    cwd: str,
    max_turns: int = 30
) -> str:
    """Run a single agent and return its final text response."""
    result_text = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeCodeOptions(
            allowed_tools=["Read", "Glob", "Grep", "Write", "Edit", "Bash"],
            max_turns=max_turns,
            cwd=cwd,
        )
    ):
        if message.type == "result":
            result_text = message.text
    return result_text
```

### 7. Parsing Modules (Deterministic, No LLM)

These replace LLM-driven file reading in the orchestrator. Regex patterns ported from existing validation scripts:

**`stage1_parser.py`**: Parse `stage-1-scope.md`
- Extract module table rows: `r"\|\s*(M-\d+)\s*\|"`
- Return `list[Module]` for modules marked "Yes"

**`stage2_parser.py`**: Parse `M-{ID}.md`
- Split by `### EP-{N}:` → extract Type, Location, Attacker-controlled data, Analysis hints
- Return `list[EntryPoint]`

No `stage3_parser.py` needed — each Stage 3 finding is already a separate self-contained
file. The orchestrator simply lists `{output_dir}/stage-3-details/*.md` to enumerate
findings for Stage 4.

## Pipeline Flow

```
Stage 0: Setup
  └─ Create output directories, write initial checkpoint

Stage 1: Orient & Scope
  └─ 1 agent → stage-1-scope.md
  └─ Validate → retry if needed
  └─ Parse → list of in-scope modules
  └─ Checkpoint: stage1=done

Stage 2: Entry Point Identification (parallel, up to max_parallel)
  ├─ Agent for M-1 → stage-2-details/M-1.md    [checkpoint each]
  ├─ Agent for M-2 → stage-2-details/M-2.md
  └─ ...
  └─ Validate each → retry if needed
  └─ Parse each → list of entry points per module

Stage 3: Vulnerability Analysis (parallel, up to max_parallel)  ← KEY CHANGE
  ├─ Agent for M-1/EP-1 → stage-3-details/M-1-EP-1-F-01.md, F-02.md, ...  [checkpoint each EP]
  ├─ Agent for M-1/EP-2 → stage-3-details/M-1-EP-2-F-01.md, ...
  ├─ Agent for M-2/EP-1 → (no files if no findings)
  └─ ...  (each finding is a separate self-contained file)
  └─ Validate each finding file → retry if needed

Stage 4: Vulnerability Evaluation (parallel, up to max_parallel)
  ├─ Orchestrator lists all *.md in stage-3-details/
  ├─ Agent per finding → stage-4-details/_pending/{stage3_filename}  [checkpoint each]
  │   (agent verifies existence, evaluates severity, writes result)
  └─ Validate each → retry if needed
  └─ Post-evaluation (deterministic):
     ├─ Read severity from each pending file
     ├─ Filter out false positives / below-Medium findings
     ├─ Assign globally unique IDs: C-01, H-01, M-01, L-01, ...
     └─ Rename to stage-4-details/{ID}.md, inject ID into file content

Stage 5: Report Generation
  └─ subprocess.run(generate_report.py)  — no agent needed
  └─ Verify output file exists
```

## Implementation Steps

### Step 1: Project scaffolding
- Create `protocol_auditor/` directory structure
- Create `pyproject.toml` with `claude-code-sdk` dependency
- Create `config.py`: dataclasses `AuditConfig`, `Module`, `EntryPoint`, `Finding`
- Create `checkpoint.py`: `CheckpointManager` class with load/save/mark_complete/is_complete

### Step 2: Parsing modules
- `stage1_parser.py` — port regex from `validate_stage1.py`
- `stage2_parser.py` — port regex from `validate_stage2.py`
- (No stage3_parser needed — findings are already separate files)
- Unit tests for each parser using sample markdown files

### Step 3: Agent utilities
- `agent_utils.py`:
  - `run_agent(prompt, cwd, allowed_tools, max_turns)` — async wrapper around `query()`
  - `run_with_validation(agent_fn, output_path, validator_script, max_retries=2)` — validation-retry loop
  - `run_parallel(tasks, semaphore)` — fan-out with concurrency control

### Step 4: Stage implementations
- `stage0_setup.py` — create directories, initialize checkpoint
- `stage1_scope.py` — build prompt from template + config, run agent, validate, parse
- `stage2_entry_points.py` — for each module: build prompt, run agent, validate, parse
- `stage3_analysis.py` — for each entry point: build prompt (single EP), run agent, validate
- `stage4_evaluation.py` — collect all findings, assign IDs, for each: build prompt, run agent, validate
- `stage5_report.py` — subprocess call to `generate_report.py`

### Step 5: Orchestrator and CLI
- `orchestrator.py` — `async def run_audit(config)`: calls stages sequentially, manages checkpoint
- `main.py` — argparse CLI:
  - `--target PATH` (required): project to audit
  - `--output-dir PATH`: output directory (default: `{target}/audit-output`)
  - `--max-parallel N`: concurrency cap (default: 4)
  - `--resume`: resume from checkpoint
  - `--threat-model TEXT`: custom threat model override
  - `--scope TEXT`: scope constraints
  - `--skip-stages LIST`: skip specific stages (for debugging)

### Step 6: Adapt prompts
- Copy `agents/*.md` → `prompts/*.md`, adapting each:
  - **Stage 3**: "Analyze this single entry point" (not "all entry points in the module")
  - **Stage 4**: Remove global ID assignment (orchestrator provides the ID)
  - **All**: Remove "reply Done/Error" instructions (SDK handles completion)
  - **All**: Remove "read your instructions from file" (prompt is injected directly)
  - **All**: Add `{placeholder}` variables for orchestrator to fill (target path, output path, etc.)

## Verification

1. **Unit test parsers**: Feed sample stage output files, verify extracted structured data
2. **Unit test checkpoint**: Create/load/resume checkpoint, verify skip logic
3. **Integration dry run**: Run against a small project with `--max-parallel 1`
4. **Parallel run**: Same project with `--max-parallel 4`, verify no race conditions on files
5. **Resume test**: Kill mid-Stage-3, restart with `--resume`, verify it picks up correctly
6. **Comparison**: Run old skill and new app on same project, compare findings and format quality

## Critical Files to Reuse

- `audit-network-protocol/script/validate_stage1.py` — reuse as-is
- `audit-network-protocol/script/validate_stage2.py` — reuse as-is
- `audit-network-protocol/script/validate_stage3.py` — reuse as-is
- `audit-network-protocol/script/validate_stage4.py` — reuse as-is
- `audit-network-protocol/script/generate_report.py` — **fix**: add markdown fence stripping to `parse_finding_file()`
- `audit-network-protocol/reference/checklist-*.md` — provide to agents based on detected language
- `audit-network-protocol/agents/*.md` — adapt into `prompts/` (source of truth for analysis methodology)
