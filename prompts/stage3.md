# Stage 3: Identify Analysis Entry Points

You are performing **Stage 3** of an orchestrated network protocol security audit. Write your analysis to disk; do not print it in your response.

## Your Task

Identify vulnerability-productive entry points for module **__MODULE_ID__**.

- **Stage 2 output**: `__STAGE2_OUTPUT_PATH__`
- **Result directory**: `__RESULT_DIR__`
- **Your module**: `__MODULE_ID__`

## Entry Point Types

- **Type P (Parser)**: Functions that deserialize raw bytes from the network into structured data.
- **Type H (Handler)**: Per-message business logic that processes already-parsed protocol messages.
- **Type S (Session)**: Cross-handler session management, authentication, and state machine logic.

## Workflow

### Step 1: Read Stage 2 Output

Read `__STAGE2_OUTPUT_PATH__` to identify project metadata, the threat model, and the module's name, description, and file paths.

### Step 2: Create Result File

Create an empty file `__RESULT_DIR__/__MODULE_ID__.md`. You will write entry points into it as you find them.

### Step 3: Identify Entry Points

Read the module's source code and identify vulnerability-productive entry points. For each:
- Determine where attacker-controlled data first enters the module
- Identify what data is attacker-controlled
- Classify the entry point type (P, H, or S)
- Note any initial validation performed
- Write analysis hints for Stage 4

Assign sequential IDs: EP-1, EP-2, EP-3, ...

**IMPORTANT:** Focus on entry points likely to yield findings — complex parsing, unsafe operations, sensitive state management. Omit trivial helpers and read-only accessors.

**Partitioning rules — read carefully before finalising the entry point list:**

1. **No source-code overlap.** Each entry point must cover a distinct, non-overlapping region of the codebase. If two candidate entry points share the same top-level function, sub-functions, or data-flow path, merge them into one entry point rather than listing them separately. Stage 4 spawns one independent sub-agent per entry point; duplicated coverage wastes tokens without producing additional findings.

2. **Size-bounded scope.** Each entry point should represent a code region that a single agent can read and trace end-to-end in one pass — roughly a call tree of up to a few hundred lines. If a parsing or handling path is very large (e.g., a dispatcher that branches into dozens of sub-handlers), split it at natural boundaries — by message type, sub-protocol, or top-level branch — so each slice is independently analyzable. Do not collapse an entire large subsystem into a single entry point.

3. **Split at stable boundaries, not arbitrary lines.** Prefer splits at public function boundaries, protocol message type switches, or clearly separate data-flow paths. A good split point is one where the two halves share no local state and an agent analyzing one half does not need to read the other.

### Step 4: Write Entry Points to Result File

Write findings incrementally to `__RESULT_DIR__/__MODULE_ID__.md` using this format for each entry point:

```markdown
### EP-{N}:
- **Type**: P (Parser) / H (Handler) / S (Session)
- **Module Name**: ...
- **Location**: `function_name` at `file:line`
- **Attacker-controlled data**: (which fields/variables are attacker-controlled)
- **Initial validation observed**: (describe validation, or "None")
- **Threat context**: (1–3 sentences: the attacker profile and the priority vulnerability classes most relevant to this entry point, drawn from the Stage 2 threat model)
- **Analysis hints**: (what Stage 4 should focus on for this specific entry point)
```

**Self-containment requirement.** Each entry point block is the sole context a Stage 4 sub-agent receives before it reads source code — the sub-agent will not load any other pipeline document. Therefore every field must be filled in with enough specificity for an agent to begin analysis without additional context. In particular:
- **Threat context** must name the attacker (e.g., "unauthenticated remote client") and the 1–3 vulnerability classes most applicable to this entry point (e.g., "integer overflow in length field, heap buffer overflow") — do not write generic placeholders.
- **Analysis hints** must describe the concrete data-flow paths or code patterns the agent should trace, not just restate the entry point type.
- **Attacker-controlled data** must name the specific variables, struct fields, or message fields that carry untrusted input into this function.

## Completion Checklist

- [ ] All vulnerability-productive entry points identified
- [ ] No two entry points cover overlapping source code regions
- [ ] Large code paths split at natural boundaries into size-bounded entry points
- [ ] Entry points written to `__RESULT_DIR__/__MODULE_ID__.md`
- [ ] Each entry point has Type, Module Name, Location, Attacker-controlled data, Initial validation observed, Analysis hints
