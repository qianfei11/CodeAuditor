# Stage 3: Vulnerability Analysis

You are performing **Stage 3** of an orchestrated software security audit. Write your findings to disk; do not print them in your response.

## Your Assignment

Read your analysis unit file at `__AU_FILE_PATH__`. It describes the codebase you are assigned to and provides the context you need to start your analysis.

Your task: discover security bugs and vulnerabilities in the assigned codebase.

## Output

For each confirmed vulnerability, write one JSON file to `__RESULT_DIR__/` named `__FINDING_PREFIX__-F-{NN}.json` (zero-padded: F-01, F-02, …).

**Each finding file must contain a single JSON object with this exact structure:**

```json
{
  "finding_id": "F-01",
  "title": "Short descriptive title",
  "location": "file:function (lines X-Y)",
  "vulnerability_class": "e.g. buffer overflow, integer underflow, use-after-free",
  "root_cause": "Brief description",
  "preliminary_severity": "Critical|High|Medium|Low",
  "code_snippet": "5-30 lines of annotated code showing the vulnerability",
  "reachability_notes": "How an attacker reaches this, prerequisites"
}
```

**Format rules** (enforced by validator):
1. The file must contain valid JSON (no trailing commas, no comments).
2. Required keys: `finding_id`, `title`, `location`, `vulnerability_class`, `root_cause`, `preliminary_severity`, `code_snippet`.
3. `preliminary_severity` must be exactly one of: `Critical`, `High`, `Medium`, `Low`.
4. `finding_id` must match the `F-{NN}` pattern from the filename.
5. One finding per file.

If no vulnerabilities are found, write no files.
