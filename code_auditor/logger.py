from __future__ import annotations

import logging
import sys

_configured = False


def configure_logging(level: str) -> None:
    global _configured
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root = logging.getLogger("code_auditor")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    _configured = True


def get_logger(name: str) -> logging.Logger:
    if not _configured:
        configure_logging("INFO")
    return logging.getLogger(f"code_auditor.{name}")
