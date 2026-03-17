# Stage 4: Vulnerability Analysis — Single Entry Point

You are performing **Stage 4** of an orchestrated network protocol security audit. Write your findings to disk; do not print them in your response.

## Your Task

Perform deep security analysis of **one specific entry point** (`__EP_ID__` in module `__MODULE_ID__`).

- **Target project**: `__TARGET_PATH__`
- **Result directory**: `__RESULT_DIR__`
- **Finding file prefix**: `__FINDING_PREFIX__` (e.g., files will be named `__FINDING_PREFIX__-F-01.md`, `__FINDING_PREFIX__-F-02.md`, etc.)

## Entry Point to Analyze

```
__EP_BLOCK__
```

## Core Methodology

Use **data-flow-driven analysis**: starting from the entry point function, trace how attacker-controlled values propagate through local variables, struct fields, function arguments, loop bounds, buffer offsets, allocation sizes, and into dangerous sinks (memory operations, system calls, response construction, state updates).

### Type-Specific Strategy

- **Type P (Parser)**: Prioritize memory safety — buffer overflows, OOB access, integer overflows in length/offset calculations, malformed input handling, truncation errors.
- **Type H (Handler)**: Prioritize logic and validation — improper field validation, injection into response construction, incorrect error handling, resource allocation from attacker-controlled values, access control.
- **Type S (Session)**: Prioritize protocol correctness — state machine transitions, auth bypass via state confusion, session fixation, incomplete cleanup, cross-handler race conditions.

## Workflow

### Step 1: Analyze the Entry Point

The entry point block above contains your threat model context: the attacker profile, priority vulnerability classes, and concrete data-flow paths to trace. Use it to guide your analysis priorities.

Read the relevant source files (use `__TARGET_PATH__` as the project root). Trace attacker-controlled data through all code paths.

**Before writing any finding, perform a static verification pass:** confirm that the vulnerable code path is actually reachable from attacker-controlled input and that no mitigating condition makes exploitation impossible. Only report a finding if you are confident it is not a false positive. A smaller set of high-confidence findings is more valuable than a large set that includes speculative ones.

For each confirmed security issue, write a separate finding file. **Each file contains exactly one finding.**

### Step 2: Write Finding Files

For each confirmed finding, write one file to `__RESULT_DIR__/` named `__FINDING_PREFIX__-F-{NN}.md` (where `{NN}` is a zero-padded two-digit number: F-01, F-02, etc.).

**Each finding file must have this exact format:**

```markdown
### F-{NN}: {Short Title}
- **Location**: `{file}:{function}` (lines {X}-{Y})
- **Vulnerability class**: {class}
- **Root cause**: {description in 1-3 sentences}
- **Preliminary severity**: {Critical|High|Medium|Low}
- **Key code snippet**:
```{lang}
{5-30 lines of annotated code showing the vulnerability}
```
- **Reachability notes**: {how an attacker reaches this, prerequisites}
```

**Self-containment requirement.** The finding file is the sole input a Stage 5 sub-agent receives before verifying the vulnerability. It must contain enough context for independent verification without loading any other pipeline document. Concretely:
- **Location** must include the exact file path, function name, and line numbers so the verifier can navigate directly to the code.
- **Root cause** must describe the specific flaw precisely enough that a reader who has not traced the data flow can understand what is wrong.
- **Key code snippet** must include the vulnerable lines with inline annotations marking where attacker-controlled data enters, what unsafe operation occurs, and what the impact is.
- **Reachability notes** must state the exact call path from the network input to this code, any preconditions (authentication state, configuration flags, message sequence), and what an attacker must send to trigger it.

**Format rules (strictly enforced by the built-in validator):**
1. Heading must be `### F-{NN}:` followed by a space and the title.
2. Required fields (each on its own `- **{name}**:` line): `Location`, `Vulnerability class`, `Root cause`, `Preliminary severity`.
3. Severity must be exactly one of: `Critical`, `High`, `Medium`, `Low`.
4. Nothing outside the finding block — no intro paragraphs, extra headings, or closing remarks.

**If no findings for this entry point:** write no files. It is valid to produce zero finding files.

## Completion Checklist

- [ ] Entry point threat context and analysis hints used to guide priorities
- [ ] Entry point source code read and analyzed
- [ ] All attacker-controlled data paths traced to dangerous sinks
- [ ] Each candidate finding statically verified as reachable and non-speculative before writing
- [ ] One finding file written per confirmed security issue (or zero files if no findings)
- [ ] Each file is self-contained and passes the Stage 4 validator's format requirements
