#!/usr/bin/env python3
"""CLI entry point for the Protocol Auditor."""

import argparse
import asyncio
import logging
import os
import sys

from .config import AuditConfig
from .orchestrator import run_audit


def _find_skill_dir() -> str:
    """Locate the audit-network-protocol directory relative to this package."""
    # Try relative to this file's location
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "audit-network-protocol"),
        os.path.join(here, "audit-network-protocol"),
    ]
    for candidate in candidates:
        if os.path.isdir(candidate):
            return os.path.abspath(candidate)
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="Network Protocol Security Auditor — SDK-based orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  protocol-auditor --target /path/to/project
  protocol-auditor --target /path/to/project --max-parallel 2 --resume
  protocol-auditor --target /path/to/project --skip-stages 1,2 --output-dir /tmp/audit
""",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Root directory of the project to audit.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: {target}/audit-output).",
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=4,
        help="Maximum number of concurrent agents (default: 4).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from a previous checkpoint.",
    )
    parser.add_argument(
        "--threat-model",
        default=None,
        help="Custom threat model override.",
    )
    parser.add_argument(
        "--scope",
        default="",
        help="Scope constraints or additional instructions for Stage 1.",
    )
    parser.add_argument(
        "--skip-stages",
        default="",
        help="Comma-separated list of stages to skip (e.g., '1,2').",
    )
    parser.add_argument(
        "--skill-dir",
        default=None,
        help="Path to audit-network-protocol/ directory (auto-detected if omitted).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Resolve paths
    target = os.path.abspath(args.target)
    if not os.path.isdir(target):
        print(f"Error: target directory not found: {target}", file=sys.stderr)
        sys.exit(1)

    output_dir = args.output_dir or os.path.join(target, "audit-output")
    output_dir = os.path.abspath(output_dir)

    skill_dir = args.skill_dir or _find_skill_dir()
    if not skill_dir or not os.path.isdir(skill_dir):
        print(
            "Error: Could not find audit-network-protocol/ directory. "
            "Use --skill-dir to specify it.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse skip stages
    skip_stages = []
    if args.skip_stages:
        try:
            skip_stages = [int(s.strip()) for s in args.skip_stages.split(",") if s.strip()]
        except ValueError:
            print("Error: --skip-stages must be comma-separated integers.", file=sys.stderr)
            sys.exit(1)

    default_threat_model = (
        "Network attacker with full control over protocol messages. "
        "The attacker can send arbitrary bytes, malformed messages, "
        "and exploit any parsing or handling vulnerability."
    )

    config = AuditConfig(
        target=target,
        output_dir=output_dir,
        skill_dir=os.path.abspath(skill_dir),
        max_parallel=args.max_parallel,
        threat_model=args.threat_model or default_threat_model,
        scope=args.scope,
        skip_stages=skip_stages,
        resume=args.resume,
    )

    try:
        report_path = asyncio.run(run_audit(config))
        print(f"\nAudit complete. Report: {report_path}")
    except KeyboardInterrupt:
        print("\nInterrupted. Run with --resume to continue.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        logging.exception("Audit failed with exception")
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
