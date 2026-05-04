from __future__ import annotations

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

_configured = False


class _ColorfulRichHandler(RichHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno == logging.DEBUG:
            record.levelname = f"[dim]{record.levelname}[/dim]"
        elif record.levelno == logging.INFO:
            record.levelname = f"[cyan]{record.levelname}[/cyan]"
        elif record.levelno == logging.WARNING:
            record.levelname = f"[yellow]{record.levelname}[/yellow]"
        elif record.levelno == logging.ERROR:
            record.levelname = f"[red]{record.levelname}[/red]"
        elif record.levelno >= logging.CRITICAL:
            record.levelname = f"[red bold]{record.levelname}[/red bold]"
        return super().emit(record)


def configure_logging(level: str) -> None:
    global _configured
    root = logging.getLogger("code_auditor")
    root.handlers.clear()
    handler = _ColorfulRichHandler(
        console=Console(stderr=True),
        show_path=False,
        show_time=True,
        markup=True,
        rich_tracebacks=True,
    )
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    _configured = True


def get_logger(name: str) -> logging.Logger:
    if not _configured:
        configure_logging("INFO")
    return logging.getLogger(f"code_auditor.{name}")
