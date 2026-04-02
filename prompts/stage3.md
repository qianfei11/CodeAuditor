# Stage 3: Codebase Scale Assessment and Analysis Unit Definition

You are performing **Stage 3** of an orchestrated software security audit. Write your output to disk; do not print it in your response.

## Your Task

Assess the codebase scale of module **__MODULE_ID__** and produce one or more **analysis unit** files that will each be assigned to an independent sub-agent for bug analysis.

- **Stage 2 output**: `__STAGE2_OUTPUT_PATH__`
- **Result directory**: `__RESULT_DIR__`
- **Your module**: `__MODULE_ID__`

## Workflow

### Step 1: Read Stage 2 Output

Read `__STAGE2_OUTPUT_PATH__` (JSON) to identify the module's name, description, and file paths.

### Step 2: Measure Codebase Scale

Enumerate the module's source files and measure their size:

- Count files and total lines of code (LOC)
- Survey the top-level structure: major subsystems, dispatch tables, protocol branches, distinct functional areas
- Determine whether a single sub-agent can analyze the full module with sufficient depth

**Scale thresholds (guidelines, not hard rules):**

| Scale | Size | Decision |
|-------|------|----------|
| Small | ≤ 800 LOC, ≤ 5 files | Single analysis unit |
| Medium | 800–2000 LOC, 5–15 files | Single analysis unit (with focused scope) |
| Large | > 2000 LOC or > 15 files | Split into multiple units |

### Step 3: Define Analysis Units and Write Output

Write **one JSON file per analysis unit** to the result directory. Name them:
- `__RESULT_DIR__/__MODULE_ID__-1.json`
- `__RESULT_DIR__/__MODULE_ID__-2.json` (if split)
- etc.

Each file is a self-contained work package for a sub-agent:

```json
{
  "description": "Short description of what this unit covers",
  "files": ["relative/path/to/file1.c", "relative/path/to/file2.c"],
  "focus": "Concrete analysis guidance: which functions or subsystems are most complex, which code paths handle external input, what data structures are central, which operations are dangerous (memory copies, size arithmetic, state transitions). Be specific enough that a sub-agent can start analysis immediately."
}
```

**Splitting rules:**

1. **Non-overlapping files.** Each unit must cover a distinct, non-overlapping set of source files.
2. **Split at stable boundaries.** Prefer protocol message type boundaries, top-level dispatch branches, or distinct functional layers.
3. **Size-bound each unit.** Aim for 500–1500 LOC per unit.
4. **Aim for 2–5 units.** If more seem necessary, reconsider — some units may be mergeable.
5. **Focus must be actionable.** Name concrete functions, data flows, or code patterns — not generic phrases.

**Output rules:**
- Each file must be valid JSON (no trailing commas, no comments)
- The `files` field must be a JSON array of strings (file paths)
- If the module needs only one analysis unit, write exactly one file: `__MODULE_ID__-1.json`

## Completion Checklist

- [ ] Stage 2 output read to obtain module name and file paths
- [ ] All source files enumerated and LOC counted
- [ ] Scale assessed and split decision made
- [ ] One JSON file per analysis unit written to `__RESULT_DIR__/`
- [ ] No overlapping files between units (if split)
- [ ] Each focus is specific and actionable
