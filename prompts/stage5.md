# Stage 5: Vulnerability Evaluation

You are performing **Stage 5** of an orchestrated network protocol security audit. Write your result to disk; do not print it in your response.

## Your Task

Evaluate one vulnerability finding from Stage 4.

- **Finding file**: `__FINDING_FILE_PATH__`
- **Output file**: `__OUTPUT_PATH__` (write here ONLY if the vulnerability is confirmed and severity ≥ Medium)
- **Severity evaluation guidance**: `__INSTRUCTION_PATH__`

## Workflow

### Step 1: Read the Finding File

Read `__FINDING_FILE_PATH__`. It contains one vulnerability finding with location, vulnerability class, root cause, preliminary severity, a code snippet, and reachability notes. The file also includes source context (module, entry point, target project path).

### Step 2: Verify Existence (False-Positive Check)

Read the relevant source code at the target project path. Perform an in-depth static analysis:
- Is the vulnerability reachable from attacker-controlled input?
- Are there any mitigating conditions that make exploitation impossible?
- Is the code path actually executed in the context described?

**If this is a false positive:** do NOT write any output file. The orchestrator will treat a missing output file as "filtered." Your task is complete — stop here.

### Step 3: Assess Pre-Requisites

Before scoring severity, determine the exact conditions required to trigger the vulnerability:

- **Compile-time flags**: Is the vulnerable code path only compiled in when a non-default or rarely-used flag is set (e.g., `#ifdef ENABLE_LEGACY_FEATURE`, an optional CMake/configure flag not enabled in typical builds)?
- **Runtime configuration**: Does triggering the vulnerability require a non-default configuration option that is unlikely to be enabled in real-world deployments?
- **Environment assumptions**: Does exploitation depend on an atypical deployment topology, hardware, or operating mode?

If the vulnerability requires a non-default compile flag or non-default runtime configuration that is uncommon in real-world deployments, cap its severity at **Medium** regardless of the theoretical impact. Document this constraint explicitly in the Pre-requisites field. The rationale: a vulnerability that most installations never expose is structurally less severe than one present in all default builds.

### Step 4: Assess Impact and Severity

Read `__INSTRUCTION_PATH__` for project-specific severity context: the attacker profile, historical severity benchmarks for this project/protocol, the highest-impact vulnerability classes, and deployment-specific modifiers that raise or lower scores.

Using this context together with your pre-requisite assessment, analyze the security impact:
- Determine what an attacker can achieve (RCE, DoS, info-leak, auth bypass, etc.)
- Compute a CVSS v3.1 base score
- Assign severity based on CVSS score:
  - **Critical**: 9.0–10.0
  - **High**: 7.0–8.9
  - **Medium**: 4.0–6.9
  - **Low**: 0.1–3.9
- Apply the non-default-config cap from Step 3 if applicable

**If severity is below Medium:** do NOT write any output file. Your task is complete — stop here.

### Step 5: Write Evaluation Result

Write your evaluation to `__OUTPUT_PATH__`. Use **exactly** this format:

```markdown
### Summary JSON Line

```json
{
  "id": "TBD",
  "title": "...",
  "location": "file:function (lines X-Y)",
  "cwe_id": ["CWE-XXX"],
  "vulnerability_class": ["class1", "class2"],
  "cvss_score": "X.X",
  "severity": "Critical|High|Medium|Low"
}
```

### Detail

- **ID**: TBD
- **Title**: (short summary)
- **Location**: (file path + function name + line numbers)
- **Vulnerability class**: (e.g., "integer overflow leading to heap buffer overflow")
- **CWE ID**: (e.g., CWE-122, CWE-190)
- **Pre-requisites**: (specific compile flags, runtime configuration options, or deployment conditions required to reach this code path; note if non-default)
- **Impact**: (RCE / DoS / info-leak / auth bypass / etc.)
- **Severity**: (Critical / High / Medium / Low — must match JSON severity)
- **Code snippet**: (paste the relevant lines with inline comments explaining the root cause and trigger path)
```

**IMPORTANT**: The `"id"` in the JSON and the `**ID**` in the Detail section must both be `TBD`. The orchestrator will assign the real ID after all evaluations complete.

**IMPORTANT**: The output file MUST be parseable by the built-in Stage 5 validator. The JSON must be valid (no trailing commas, properly quoted strings).

## Completion Checklist

- [ ] Finding file read and source code verified
- [ ] False-positive check performed
- [ ] Pre-requisites assessed (compile flags, runtime config, deployment assumptions)
- [ ] Severity evaluation guidance read (`__INSTRUCTION_PATH__`)
- [ ] Non-default-config cap applied if applicable
- [ ] If confirmed and severity ≥ Medium: output written to `__OUTPUT_PATH__`
- [ ] If false positive or < Medium: no output file written
