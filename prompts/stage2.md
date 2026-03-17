# Stage 2: Orient and Scope

You are performing **Stage 2** of an orchestrated network protocol security audit. Write your analysis to disk; do not print it in your response.

## Your Task

Analyze the project at **__TARGET_PATH__** and produce a scope document at **__OUTPUT_PATH__**.

- **Research report**: `__RESEARCH_PATH__`
- **Initial threat model**: __THREAT_MODEL__

## User Instructions

__USER_INSTRUCTIONS__

## Workflow

### Step 1: Read the Research Report

Read `__RESEARCH_PATH__` completely before doing anything else. Extract:

- **Threat Model Conclusions** — Priority Vulnerability Classes, Out of Scope, Attacker Profile, and High-Risk Modules and Subsystems
- **Vulnerability Patterns for Follow-On Audit** — recurring weakness types to prioritize
- Any modules or subsystems explicitly flagged as high-risk

This report is the primary input for threat model finalization and module scoping. High-Risk Modules listed there should default to `Yes` for Stage 3 analysis unless there is a strong reason to exclude them.

### Step 2: Understand the Protocol (if needed)

This step is only necessary if the protocol(s) implemented by the project is a custom or uncommon protocol. For well-known protocols (HTTP, DNS, FTP, etc.), skip to Step 3.

Gather information about the protocol from:
- The project's documentation, README, or design documents
- Source files that define message structures, parsing code, or state machines

### Step 3: Determine Implementation Role

Determine whether the project implements the **client side**, **server side**, or **both sides** of the protocol:

- **Server-side**: The attacker is a malicious client sending crafted requests.
- **Client-side**: The attacker is a malicious server (or MITM) replying with crafted messages.
- **Both**: Both sides must be audited independently.

### Step 4: Finalize Threat Model

Combine the following inputs to produce a concise, final threat model statement:

1. The **Threat Model Conclusions** from `__RESEARCH_PATH__` (primary source — historical evidence takes precedence)
2. The initial threat model provided above
3. The user instructions
4. Any project security policy found in the repository

The final threat model must name: the attacker, their capabilities, the attack surface, which vulnerability classes are priority focus, and which issues are out of scope.

### Step 5: Enumerate Modules and Protocol Implementations

Identify the project's structure and group related source files into **modules** that implement a cohesive protocol or subsystem. For each module, decide whether it falls within the audit scope and is vulnerability-productive enough for deeper analysis.

Cross-reference the **High-Risk Modules and Subsystems** from the research report — those should default to `Yes` unless there is a strong reason to exclude them.

**IMPORTANT:** Each module will be processed independently. Ensure modules are self-contained and cohesive.

### Step 6: Write Output

Write your output to **__OUTPUT_PATH__** using the available file editing tools. The file must have this exact structure:

```markdown
# Orient and Scope

## Project Summary
(project path, name, language, brief description of functionality and protocols, client/server role)

## Threat Model
(final threat model, derived from research conclusions + initial threat model + user instructions)

## Module Structure

| ID | Module | Description | Files / Directory | Analyze in Stage 3 |
|----|--------|-------------|-------------------|--------------------|
| M-1 | [name] | [short description] | [files or dir] | Yes / No |
| M-2 | ... | ... | ... | ... |
```

**IMPORTANT**: Write the output to **__OUTPUT_PATH__** using the available file editing tools. Do not return the content in your response.

## Completion Checklist

- [ ] Research report read and Threat Model Conclusions extracted
- [ ] Protocol(s) understood or confirmed well-known
- [ ] Client/server role identified
- [ ] Threat model finalized (incorporating research conclusions as primary input)
- [ ] Modules enumerated with analysis verdicts (high-risk modules from research defaulting to Yes)
- [ ] Output written to **__OUTPUT_PATH__**
