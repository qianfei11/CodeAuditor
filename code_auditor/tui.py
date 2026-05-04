"""Terminal User Interface for CodeAuditor using Rich.

Provides a beautiful dashboard that shows:
- Audit configuration summary
- Stage-by-stage progress with spinners
- Live log output
- Final results summary
"""
from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.logging import RichHandler
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

# ── Colour palette ──────────────────────────────────────────────────────────
ACCENT = "cyan"
ACCENT2 = "magenta"
SUCCESS = "green"
WARN = "yellow"
ERROR = "red"
DIM = "dim"
BOLD = "bold"

# ── Stage metadata ──────────────────────────────────────────────────────────
STAGE_INFO: dict[int, tuple[str, str]] = {
    0: ("Init", "Git clone + output directory setup"),
    1: ("Context", "Security context research"),
    2: ("Decompose", "Decompose codebase into analysis units"),
    3: ("Discover", "Bug discovery per analysis unit"),
    4: ("Evaluate", "Evaluate findings as vulnerabilities"),
    5: ("PoC", "Proof-of-concept reproduction"),
    6: ("Disclose", "Disclosure package preparation"),
}


@dataclass
class _StageState:
    """Mutable state for a single stage."""
    status: str = "pending"  # pending | running | done | skipped | failed
    detail: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    items_done: int = 0
    items_total: int = 0


@dataclass
class TUIState:
    """Shared state consumed by the live dashboard render function."""
    target: str = ""
    output_dir: str = ""
    wiki_path: str = ""
    backend: str = ""
    model: str = ""
    max_parallel: int = 1
    stages: dict[int, _StageState] = field(default_factory=dict)
    log_lines: list[str] = field(default_factory=list)
    max_log_lines: int = 40
    finished: bool = False
    error: str = ""
    start_time: float = 0.0


# ── Logging handler that feeds the TUI ─────────────────────────────────────

class _TUILogHandler(logging.Handler):
    """Captures log records and appends formatted lines to TUIState."""

    def __init__(self, state: TUIState) -> None:
        super().__init__()
        self._state = state

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if record.levelno == logging.DEBUG:
                msg = f"[dim]{msg}[/dim]"
            elif record.levelno == logging.INFO:
                msg = f"[cyan]{msg}[/cyan]"
            elif record.levelno == logging.WARNING:
                msg = f"[yellow]{msg}[/yellow]"
            elif record.levelno == logging.ERROR:
                msg = f"[red]{msg}[/red]"
            elif record.levelno >= logging.CRITICAL:
                msg = f"[red bold]{msg}[/red bold]"
            self._state.log_lines.append(msg)
            if len(self._state.log_lines) > self._state.max_log_lines:
                self._state.log_lines = self._state.log_lines[-self._state.max_log_lines:]
        except Exception:
            self.handleError(record)


# ── Dashboard renderer ──────────────────────────────────────────────────────

def _make_header() -> Panel:
    title = Text()
    title.append("⚡ ", style=SUCCESS)
    title.append("Code", style=f"{BOLD} {ACCENT}")
    title.append("Auditor", style=f"{BOLD} {ACCENT2}")
    title.append(" ⚡", style=SUCCESS)
    return Panel(title, style=f"bold {ACCENT}", border_style=ACCENT, padding=(0, 2))


def _make_config_table(state: TUIState) -> Table:
    table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    table.add_column("Key", style=DIM, width=16)
    table.add_column("Value", style=BOLD)
    table.add_row("Target", state.target)
    table.add_row("Output", state.output_dir)
    table.add_row("Wiki", state.wiki_path or "—")
    table.add_row("Backend", f"{state.backend}  ({state.model or 'default'})")
    table.add_row("Parallel", str(state.max_parallel))
    elapsed = time.time() - state.start_time if state.start_time else 0
    table.add_row("Elapsed", _fmt_duration(elapsed))
    return table


def _fmt_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _make_stage_panel(state: TUIState) -> Panel:
    table = Table(show_header=True, header_style=f"bold {ACCENT}", box=None, padding=(0, 1), expand=True)
    table.add_column("#", width=3, justify="center")
    table.add_column("Stage", width=12)
    table.add_column("Description", ratio=3)
    table.add_column("Status", width=14, justify="center")
    table.add_column("Progress", width=14, justify="right")
    table.add_column("Time", width=10, justify="right")

    for stage_num in sorted(STAGE_INFO.keys()):
        name, desc = STAGE_INFO[stage_num]
        st = state.stages.get(stage_num, _StageState())

        # Status display
        if st.status == "pending":
            status_text = Text("⏳ pending", style=DIM)
        elif st.status == "running":
            status_text = Text("▶ running", style=f"{BOLD} {WARN}")
        elif st.status == "done":
            status_text = Text("✔ done", style=SUCCESS)
        elif st.status == "skipped":
            status_text = Text("⏭ skipped", style=DIM)
        elif st.status == "failed":
            status_text = Text("✘ failed", style=ERROR)
        else:
            status_text = Text(st.status)

        # Progress
        if st.items_total > 0:
            pct = st.items_done / st.items_total
            bar_len = 8
            filled = int(pct * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            progress_text = f"{bar} {st.items_done}/{st.items_total}"
        elif st.status == "running":
            progress_text = ""
        else:
            progress_text = ""

        # Time
        if st.start_time and st.end_time:
            time_text = _fmt_duration(st.end_time - st.start_time)
        elif st.start_time and st.status == "running":
            time_text = _fmt_duration(time.time() - st.start_time)
        else:
            time_text = ""

        detail = st.detail or desc
        table.add_row(str(stage_num), name, detail, status_text, progress_text, time_text)

    return Panel(table, title="[bold]Pipeline Stages[/bold]", border_style=ACCENT, padding=(1, 1), height=10)


def _make_log_panel(state: TUIState) -> Panel:
    if not state.log_lines:
        content = Text("Waiting for logs...", style=DIM)
    else:
        content = Text("\n".join(state.log_lines[-state.max_log_lines:]))
    return Panel(
        content,
        title="[bold]Live Log[/bold]",
        border_style=DIM,
        padding=(0, 1),
    )


def _make_summary(state: TUIState) -> Panel:
    elapsed = _fmt_duration(time.time() - state.start_time) if state.start_time else "—"
    done = sum(1 for s in state.stages.values() if s.status == "done")
    failed = sum(1 for s in state.stages.values() if s.status == "failed")
    skipped = sum(1 for s in state.stages.values() if s.status == "skipped")

    tree = Tree("[bold]Audit Summary[/bold]")
    tree.add(f"Elapsed: [cyan]{elapsed}[/cyan]")
    tree.add(f"Stages completed: [green]{done}[/green]")
    if failed:
        tree.add(f"Stages failed: [red]{failed}[/red]")
    if skipped:
        tree.add(f"Stages skipped: [dim]{skipped}[/dim]")
    if state.error:
        tree.add(f"Error: [red]{state.error}[/red]")
    return Panel(tree, border_style=SUCCESS if not state.error else ERROR, padding=(1, 2))


def _render_dashboard(state: TUIState) -> Layout:
    """Build the full dashboard layout."""
    layout = Layout()
    layout.split_column(
        Layout(_make_header(), size=3, name="header"),
        Layout(name="body"),
    )

    body_children = [
        Layout(_make_config_table(state), size=7, name="config"),
        Layout(_make_stage_panel(state), name="stages"),
        Layout(_make_log_panel(state), name="logs"),
    ]

    if state.finished:
        body_children.append(Layout(_make_summary(state), size=8, name="summary"))

    layout["body"].split_column(*body_children)
    return layout


# ── Public API ──────────────────────────────────────────────────────────────

class TUIManager:
    """Manages the Rich live dashboard for CodeAuditor.

    Usage::

        tui = TUIManager()
        tui.configure(target="/path", output_dir="...", backend="claude", ...)
        tui.start()

        # Inside orchestrator:
        tui.begin_stage(1)
        tui.stage_progress(1, items_done=3, items_total=10)
        tui.end_stage(1)

        tui.stop()
    """

    def __init__(self) -> None:
        self._state = TUIState()
        self._console = Console()
        self._live: Live | None = None
        self._log_handler: _TUILogHandler | None = None
        self._refresh_thread: threading.Thread | None = None
        self._stop_refresh = threading.Event()

    # ── Configuration ───────────────────────────────────────────────────

    def configure(
        self,
        *,
        target: str,
        output_dir: str,
        wiki_path: str | None,
        backend: str,
        model: str | None,
        max_parallel: int,
    ) -> None:
        self._state.target = target
        self._state.output_dir = output_dir
        self._state.wiki_path = wiki_path or ""
        self._state.backend = backend
        self._state.model = model or "default"
        self._state.max_parallel = max_parallel

    # ── Lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the live dashboard and install the log handler."""
        self._state.start_time = time.time()

        # Install log handler
        self._log_handler = _TUILogHandler(self._state)
        self._log_handler.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
        self._log_handler.setFormatter(fmt)

        root_logger = logging.getLogger("code_auditor")
        root_logger.addHandler(self._log_handler)

        # Start live display
        self._live = Live(
            _render_dashboard(self._state),
            console=self._console,
            refresh_per_second=4,
            screen=True,
            vertical_overflow="visible",
        )
        self._live.start()

        # Background thread to keep elapsed/progress updated while stage is running
        def _bg_refresh() -> None:
            while not self._stop_refresh.is_set():
                self._refresh()
                self._stop_refresh.wait(0.25)

        self._stop_refresh.clear()
        self._refresh_thread = threading.Thread(target=_bg_refresh, daemon=True)
        self._refresh_thread.start()

    def stop(self) -> None:
        """Stop the live display and remove the log handler."""
        self._state.finished = True
        self._stop_refresh.set()
        if self._refresh_thread:
            self._refresh_thread.join(timeout=1.0)
            self._refresh_thread = None
        if self._live:
            self._live.refresh()
            time.sleep(0.1)
            self._live.stop()
            self._live = None

        if self._log_handler:
            root_logger = logging.getLogger("code_auditor")
            root_logger.removeHandler(self._log_handler)
            self._log_handler = None

        # Print final summary to console
        self._console.print()
        self._console.print(_make_summary(self._state))
        self._console.print()

    def _refresh(self) -> None:
        if self._live:
            self._live.update(_render_dashboard(self._state))

    # ── Stage events ────────────────────────────────────────────────────

    def begin_stage(self, stage_num: int, detail: str = "") -> None:
        st = _StageState(status="running", detail=detail, start_time=time.time())
        self._state.stages[stage_num] = st
        self._refresh()

    def end_stage(self, stage_num: int, *, success: bool = True) -> None:
        st = self._state.stages.get(stage_num)
        if st:
            st.status = "done" if success else "failed"
            st.end_time = time.time()
            self._refresh()

    def skip_stage(self, stage_num: int, detail: str = "") -> None:
        st = _StageState(status="skipped", detail=detail or "Skipped by user")
        self._state.stages[stage_num] = st
        self._refresh()

    def stage_progress(
        self,
        stage_num: int,
        *,
        items_done: int = 0,
        items_total: int = 0,
        detail: str = "",
    ) -> None:
        st = self._state.stages.get(stage_num)
        if st:
            st.items_done = items_done
            st.items_total = items_total
            if detail:
                st.detail = detail
            self._refresh()

    def set_error(self, message: str) -> None:
        self._state.error = message
        self._refresh()


# ── Convenience: configure Rich logging for non-TUI mode ────────────────────

def configure_rich_logging(level: str) -> None:
    """Replace the default stderr handler with a RichHandler for prettier non-TUI logs."""
    root = logging.getLogger("code_auditor")
    root.handlers.clear()
    handler = RichHandler(
        console=Console(stderr=True),
        show_path=False,
        show_time=True,
        markup=True,
        rich_tracebacks=True,
    )
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))