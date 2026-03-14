"""Agent spawning, validation-retry, and concurrency utilities."""

import asyncio
import logging
import os
import subprocess
from typing import Optional

from claude_code_sdk import query, ClaudeCodeOptions

logger = logging.getLogger(__name__)

DEFAULT_TOOLS = ["Read", "Glob", "Grep", "Write", "Edit", "Bash"]


async def run_agent(
    prompt: str,
    cwd: str,
    allowed_tools: list[str] = DEFAULT_TOOLS,
    max_turns: int = 30,
) -> str:
    """Run a single Claude agent and return its final text response."""
    result_text = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeCodeOptions(
            allowed_tools=allowed_tools,
            max_turns=max_turns,
            cwd=cwd,
        ),
    ):
        if hasattr(message, "type") and message.type == "result":
            result_text = getattr(message, "text", "") or ""
    return result_text


async def run_with_validation(
    prompt: str,
    cwd: str,
    output_path: str,
    validator_script: str,
    max_retries: int = 2,
    allowed_tools: list[str] = DEFAULT_TOOLS,
    max_turns: int = 30,
    skip_if_missing: bool = False,
) -> tuple[bool, str]:
    """
    Run an agent, then validate its output file.
    If validation fails, run a focused repair agent with the error messages.
    Returns (passed, final_result_text).

    If skip_if_missing=True, a missing output file is treated as "filtered" (not an error).
    """
    result = await run_agent(prompt, cwd, allowed_tools, max_turns)

    for attempt in range(max_retries + 1):
        # If output file is missing and that's allowed, return success
        if skip_if_missing and not os.path.exists(output_path):
            logger.info(f"No output file at {output_path} (finding filtered or no findings)")
            return True, result

        validation = run_validator(validator_script, output_path)
        if validation.returncode == 0:
            logger.info(f"Validation passed for {output_path}")
            return True, result

        if attempt == max_retries:
            logger.warning(
                f"Validation failed after {max_retries} retries for {output_path}:\n"
                f"{validation.stdout}"
            )
            return False, result

        # Repair pass
        logger.info(f"Validation failed (attempt {attempt + 1}/{max_retries}), running repair...")
        issues = validation.stdout.strip()
        repair_prompt = (
            f"The output file at `{output_path}` failed validation. "
            f"Please fix all issues listed below, then save the corrected file.\n\n"
            f"Validation output:\n```\n{issues}\n```"
        )
        result = await run_agent(repair_prompt, cwd, allowed_tools, max_turns=10)

    return False, result


def run_validator(script_path: str, file_path: str) -> subprocess.CompletedProcess:
    """Run a validation script and return the result."""
    return subprocess.run(
        ["python3", script_path, "--file", file_path],
        capture_output=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


async def run_parallel(
    tasks: list,
    semaphore: asyncio.Semaphore,
) -> list:
    """Run async tasks in parallel, respecting a semaphore for concurrency control."""
    async def run_with_sem(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*[run_with_sem(t) for t in tasks], return_exceptions=True)


def load_prompt(prompt_path: str, **substitutions: str) -> str:
    """Load a prompt template file and substitute placeholders."""
    with open(prompt_path) as f:
        text = f.read()
    for key, value in substitutions.items():
        text = text.replace(f"__{key.upper()}__", value)
    return text
