# Stage 2: Module Structure

You are performing **Stage 2** of an orchestrated software security audit. Write your output to disk; do not print it in your response.

## Your Task

Analyze the project at **__TARGET_PATH__** and decompose it into functional modules. Each module groups one or more related source files that implement a cohesive piece of functionality.

- **Output file**: `__OUTPUT_PATH__`

## User Instructions

__USER_INSTRUCTIONS__

## Workflow

### Step 1: Enumerate Source Files

List all source files in **__TARGET_PATH__**. Focus on implementation files (`.c`, `.cpp`, `.go`, `.rs`, `.py`, `.java`, `.ts`, etc.). Exclude: build artifacts, test files (`*_test.*`, `*.test.*`, `test/`, `tests/`), generated code, and third-party vendored dependencies.

### Step 2: Understand the Project

Read key project files to understand the project's purpose and architecture:
- `README*`, build files (`Makefile`, `CMakeLists.txt`, `go.mod`, `Cargo.toml`, `package.json`, etc.)
- Directory structure and naming conventions
- Top-level source files that define the main entry points or architecture

### Step 3: Group Files into Functional Modules

Group related source files into modules based on what the code **does**, not where it lives. Each module should:

- Implement a cohesive feature, subsystem, or protocol component
- Contain one or more files — every source file must belong to exactly one module
- Have a clear, descriptive name that reflects its function

Good split boundaries:
- Protocol parsing vs. protocol handling vs. session/state management
- Different protocol versions or message types
- Core logic vs. I/O vs. configuration vs. utility code
- Independent subsystems with minimal coupling

Do not split purely by directory — group by functionality. Do not merge unrelated subsystems into one module just because they share a directory.

### Step 4: Write Output

Write your output to **__OUTPUT_PATH__** as a JSON object with this exact structure:

```json
{
  "project_summary": {
    "path": "__TARGET_PATH__",
    "name": "project name",
    "language": "primary language",
    "description": "Brief description of what the project does"
  },
  "modules": [
    {
      "id": "M-1",
      "name": "module name",
      "description": "description of what this module does",
      "files": ["file paths or directory (e.g. src/parser/ or src/foo.c, src/bar.c)"]
    }
  ]
}
```

**Rules:**
- Every source file must appear in exactly one module (no omissions, no overlap)
- Module IDs must follow the pattern `M-1`, `M-2`, `M-3`, ...
- Descriptions must describe what the code *does*, not just where it lives
- The `files` field may be a directory path (e.g., `src/parser/`) if all files in it belong to this module, or a comma-separated list of individual relative file paths
- The output must be valid JSON (no trailing commas, properly quoted strings)

## Completion Checklist

- [ ] All source files enumerated (excluding tests, generated code, third-party deps)
- [ ] Files grouped into cohesive functional modules with no overlaps or omissions
- [ ] Each module has a clear, functional name and a concrete one-line description
- [ ] Output written to **__OUTPUT_PATH__** as valid JSON with `project_summary` and `modules` fields
- [ ] All module IDs follow the `M-N` pattern
