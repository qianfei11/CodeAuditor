from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import sys
import threading
import tomllib

import pytest
from rich.table import Table
from rich.text import Text

from code_auditor import __main__ as main_module
from code_auditor import agent
from code_auditor import logger as logger_module
from code_auditor.__main__ import _build_parser
from code_auditor.config import (
    DEFAULT_AGENT_TIMEOUT_SECONDS,
    DEFAULT_BACKEND,
    DEFAULT_CLAUDE_POC_MODEL,
    DEFAULT_CODEX_POC_MODEL,
    AgentBackend,
    AuditConfig,
    select_poc_model,
)
from code_auditor.tui import TUIManager, TUIState, _TUILogHandler, _make_log_panel, _visible_log_lines


def test_cli_backend_defaults_to_claude() -> None:
    args = _build_parser().parse_args(["--target", "."])

    assert args.backend == DEFAULT_BACKEND == "claude"
    assert args.model is None


def test_cli_accepts_codex_backend_and_model_override() -> None:
    args = _build_parser().parse_args([
        "--target",
        ".",
        "--backend",
        "codex",
        "--model",
        "gpt-5.4",
    ])

    assert args.backend == "codex"
    assert args.model == "gpt-5.4"


def test_cli_rejects_opencode_backend() -> None:
    with pytest.raises(SystemExit) as exc:
        _build_parser().parse_args([
            "--target",
            ".",
            "--backend",
            "opencode",
        ])

    assert exc.value.code == 2


def test_cli_accepts_wiki_path() -> None:
    args = _build_parser().parse_args([
        "--target",
        ".",
        "--wiki",
        "/tmp/wiki",
    ])

    assert args.wiki == "/tmp/wiki"


def test_main_maps_wiki_path_to_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, AuditConfig] = {}
    target = tmp_path / "target"
    wiki = tmp_path / "wiki"
    target.mkdir()
    wiki.mkdir()

    async def fake_run_audit(config: AuditConfig) -> None:
        captured["config"] = config

    monkeypatch.setattr(main_module, "run_audit", fake_run_audit)
    monkeypatch.setattr(sys, "argv", [
        "code-auditor",
        "--target",
        str(target),
        "--wiki",
        str(wiki),
    ])

    main_module.main()

    assert captured["config"].wiki_path == str(wiki.resolve())


def test_main_logs_loaded_wiki_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    target = tmp_path / "target"
    wiki = tmp_path / "wiki"
    target.mkdir()
    wiki.mkdir()

    async def fake_run_audit(config: AuditConfig) -> None:
        assert config.wiki_path == str(wiki.resolve())

    monkeypatch.setattr(main_module, "run_audit", fake_run_audit)
    monkeypatch.setattr(sys, "argv", [
        "code-auditor",
        "--target",
        str(target),
        "--wiki",
        str(wiki),
    ])

    with caplog.at_level(logging.INFO, logger="code_auditor.main"):
        main_module.main()

    wiki_path = str(wiki.resolve())
    assert wiki_path in caplog.text


def test_main_rejects_missing_wiki_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "target"
    missing_wiki = tmp_path / "missing-wiki"
    target.mkdir()

    monkeypatch.setattr(sys, "argv", [
        "code-auditor",
        "--target",
        str(target),
        "--wiki",
        str(missing_wiki),
    ])

    with pytest.raises(SystemExit) as exc:
        main_module.main()

    assert exc.value.code == 1
    assert f"Error: Wiki directory not found: {missing_wiki.resolve()}" in capsys.readouterr().err


def test_main_rejects_wiki_file_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "target"
    wiki_file = tmp_path / "wiki.md"
    target.mkdir()
    wiki_file.write_text("# Not a directory\n")

    monkeypatch.setattr(sys, "argv", [
        "code-auditor",
        "--target",
        str(target),
        "--wiki",
        str(wiki_file),
    ])

    with pytest.raises(SystemExit) as exc:
        main_module.main()

    assert exc.value.code == 1
    assert f"Error: Wiki path is not a directory: {wiki_file.resolve()}" in capsys.readouterr().err


def test_additional_directories_includes_existing_wiki_path(tmp_path) -> None:  # type: ignore[no-untyped-def]
    target = tmp_path / "target"
    output = tmp_path / "output"
    wiki = tmp_path / "wiki"
    target.mkdir()
    output.mkdir()
    wiki.mkdir()
    config = AuditConfig(
        target=str(target),
        output_dir=str(output),
        wiki_path=str(wiki),
    )

    assert agent._additional_directories(config, str(target)) == [
        str(output.resolve()),
        str(wiki.resolve()),
    ]


def test_additional_directories_skips_wiki_when_it_is_cwd(tmp_path) -> None:  # type: ignore[no-untyped-def]
    target = tmp_path / "target"
    output = tmp_path / "output"
    target.mkdir()
    output.mkdir()
    config = AuditConfig(
        target=str(target),
        output_dir=str(output),
        wiki_path=str(target),
    )

    assert agent._additional_directories(config, str(target)) == [str(output.resolve())]


def test_cli_accepts_enable_timeout() -> None:
    args = _build_parser().parse_args([
        "--target",
        ".",
        "--enable-timeout",
    ])

    assert args.enable_timeout is True


def test_audit_config_disables_timeout_by_default() -> None:
    config = AuditConfig(target="/tmp/project", output_dir="/tmp/output")

    assert config.agent_timeout_seconds is None


def test_cli_rejects_disable_timeout_option() -> None:
    with pytest.raises(SystemExit) as exc:
        _build_parser().parse_args([
            "--target",
            ".",
            "--disable-timeout",
        ])

    assert exc.value.code == 2


def test_cli_rejects_audit_only_option() -> None:
    with pytest.raises(SystemExit) as exc:
        _build_parser().parse_args([
            "--target",
            ".",
            "--audit-only",
        ])

    assert exc.value.code == 2


def test_cli_rejects_disable_reproduction_timeout_option() -> None:
    with pytest.raises(SystemExit) as exc:
        _build_parser().parse_args([
            "--target",
            ".",
            "--disable-reproduction-timeout",
        ])

    assert exc.value.code == 2


def test_main_disables_timeout_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, AuditConfig] = {}

    async def fake_run_audit(config: AuditConfig) -> None:
        captured["config"] = config

    monkeypatch.setattr(main_module, "run_audit", fake_run_audit)
    monkeypatch.setattr(sys, "argv", [
        "code-auditor",
        "--target",
        str(tmp_path),
    ])

    main_module.main()

    assert captured["config"].agent_timeout_seconds is None


def test_main_maps_enable_timeout_to_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, AuditConfig] = {}

    async def fake_run_audit(config: AuditConfig) -> None:
        captured["config"] = config

    monkeypatch.setattr(main_module, "run_audit", fake_run_audit)
    monkeypatch.setattr(sys, "argv", [
        "code-auditor",
        "--target",
        str(tmp_path),
        "--enable-timeout",
    ])

    main_module.main()

    assert captured["config"].agent_timeout_seconds == DEFAULT_AGENT_TIMEOUT_SECONDS


def test_main_exits_130_on_keyboard_interrupt(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main_module._exit_after_keyboard_interrupt()

    assert exc.value.code == 130
    assert "Interrupted by user." in capsys.readouterr().err


def test_tui_mode_exits_nonzero_after_audit_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    target = tmp_path / "target"
    target.mkdir()

    class FakeTUIManager:
        def configure(self, **_kwargs) -> None:  # type: ignore[no-untyped-def]
            pass

        def start(self) -> None:
            pass

        def set_error(self, _message: str) -> None:
            pass

        def wait_for_exit(self) -> None:
            pass

    async def failing_run_audit(*_args, **_kwargs) -> None:  # type: ignore[no-untyped-def]
        raise RuntimeError("audit failed")

    monkeypatch.setattr(main_module, "TUIManager", FakeTUIManager)
    monkeypatch.setattr(main_module, "run_audit", failing_run_audit)
    monkeypatch.setattr(sys, "argv", [
        "code-auditor",
        "--target",
        str(target),
        "--tui",
    ])

    with pytest.raises(SystemExit) as exc:
        main_module.main()

    assert exc.value.code == 1


@pytest.mark.parametrize(
    ("backend", "config_model", "expected_model"),
    [
        ("claude", None, DEFAULT_CLAUDE_POC_MODEL),
        ("codex", None, DEFAULT_CODEX_POC_MODEL),
        ("claude", "custom-global-model", "custom-global-model"),
        ("codex", "custom-global-model", "custom-global-model"),
    ],
)
def test_select_poc_model_prefers_global_model_override(
    backend: AgentBackend,
    config_model: str | None,
    expected_model: str,
) -> None:
    config = AuditConfig(
        target="/tmp/project",
        output_dir="/tmp/output",
        backend=backend,
        model=config_model,
    )

    assert select_poc_model(config) == expected_model


def test_resolve_codex_bin_uses_default_path(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    codex_bin = tmp_path / "codex"
    codex_bin.write_text("#!/bin/sh\n")
    codex_bin.chmod(0o755)
    monkeypatch.setattr(agent, "DEFAULT_CODEX_BIN", str(codex_bin))

    assert agent._resolve_codex_bin() == str(codex_bin)


def test_resolve_codex_bin_rejects_missing_default(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    missing = tmp_path / "missing-codex"
    monkeypatch.setattr(agent, "DEFAULT_CODEX_BIN", str(missing))

    with pytest.raises(RuntimeError, match="Codex CLI binary not found"):
        agent._resolve_codex_bin()


def test_project_dependencies_do_not_include_opencode() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())

    assert all("opencode" not in dependency.lower() for dependency in pyproject["project"]["dependencies"])


def test_run_agent_dispatches_to_codex_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run_case() -> None:
        async def fake_codex_agent(*_args, **_kwargs) -> str:  # type: ignore[no-untyped-def]
            return "codex-result"

        async def fake_claude_agent(*_args, **_kwargs) -> str:  # type: ignore[no-untyped-def]
            raise AssertionError("Claude backend should not be called")

        monkeypatch.setattr(agent, "_run_codex_agent", fake_codex_agent)
        monkeypatch.setattr(agent, "_run_claude_agent", fake_claude_agent)

        config = AuditConfig(target="/tmp/project", output_dir="/tmp/output", backend="codex")

        assert await agent.run_agent("prompt", config, cwd="/tmp/project") == "codex-result"

    asyncio.run(run_case())


def test_run_agent_rejects_stale_opencode_backend() -> None:
    async def run_case() -> None:
        config = AuditConfig(
            target="/tmp/project",
            output_dir="/tmp/output",
            backend="opencode",  # type: ignore[arg-type]
        )

        with pytest.raises(ValueError, match="Unsupported agent backend: opencode"):
            await agent.run_agent("prompt", config, cwd="/tmp/project")

    asyncio.run(run_case())


def test_run_agent_logs_subagent_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def run_case() -> None:
        async def fake_codex_agent(*_args, **_kwargs) -> str:  # type: ignore[no-untyped-def]
            return "codex-result"

        async def fake_claude_agent(*_args, **_kwargs) -> str:  # type: ignore[no-untyped-def]
            raise AssertionError("Claude backend should not be called")

        monkeypatch.setattr(agent, "_run_codex_agent", fake_codex_agent)
        monkeypatch.setattr(agent, "_run_claude_agent", fake_claude_agent)

        config = AuditConfig(target="/tmp/project", output_dir="/tmp/output", backend="codex")

        with caplog.at_level(logging.INFO, logger="code_auditor.agent"):
            assert await agent.run_agent("prompt", config, cwd="/tmp/project") == "codex-result"

        lifecycle_messages = [
            record.getMessage()
            for record in caplog.records
            if record.name == "code_auditor.agent" and record.levelno == logging.INFO
        ]
        assert any("Creating codex subagent" in message for message in lifecycle_messages)
        assert any(
            "Destroyed codex subagent" in message and "status=completed" in message
            for message in lifecycle_messages
        )

    asyncio.run(run_case())


def test_run_agent_logs_subagent_destruction_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def run_case() -> None:
        async def fake_codex_agent(*_args, **_kwargs) -> str:  # type: ignore[no-untyped-def]
            raise RuntimeError("backend failed")

        monkeypatch.setattr(agent, "_run_codex_agent", fake_codex_agent)

        config = AuditConfig(target="/tmp/project", output_dir="/tmp/output", backend="codex")

        with caplog.at_level(logging.INFO, logger="code_auditor.agent"):
            with pytest.raises(RuntimeError, match="backend failed"):
                await agent.run_agent("prompt", config, cwd="/tmp/project")

        lifecycle_messages = [
            record.getMessage()
            for record in caplog.records
            if record.name == "code_auditor.agent" and record.levelno == logging.INFO
        ]
        assert any(
            "Destroyed codex subagent" in message and "status=failed" in message
            for message in lifecycle_messages
        )

    asyncio.run(run_case())


def test_claude_backend_keeps_claude_code_settings_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run_case() -> None:
        captured: dict[str, dict[str, str | None]] = {}

        class FakeClaudeCodeOptions:
            extra_args: dict[str, str | None]

            def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
                self.__dict__.update(kwargs)

        async def fake_query(*, prompt: str, options: FakeClaudeCodeOptions):  # type: ignore[no-untyped-def]
            captured["extra_args"] = options.extra_args
            if False:
                yield None

        monkeypatch.setattr(agent, "_load_claude_sdk", lambda: (FakeClaudeCodeOptions, fake_query))

        config = AuditConfig(target="/tmp/project", output_dir="/tmp/output", backend="claude")

        await agent.run_agent("prompt", config, cwd="/tmp/project")

        assert "setting-sources" not in captured["extra_args"]

    asyncio.run(run_case())


def test_tui_log_handler_retains_history_beyond_visible_limit() -> None:
    state = TUIState(max_log_lines=2, max_log_history=10)
    handler = _TUILogHandler(state)

    for index in range(3):
        handler.emit(logging.LogRecord(
            name="code_auditor.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=0,
            msg="message %s",
            args=(index,),
            exc_info=None,
        ))

    assert len(state.log_lines) == 3


def test_tui_log_handler_splits_multiline_records_into_scrollable_rows() -> None:
    state = TUIState(max_log_lines=2, max_log_history=10)
    handler = _TUILogHandler(state)

    handler.emit(logging.LogRecord(
        name="code_auditor.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg="first row\nsecond row\nthird row",
        args=(),
        exc_info=None,
    ))

    assert len(state.log_lines) == 3
    assert "first row" in state.log_lines[0].plain
    assert state.log_lines[1].plain == "second row"
    assert state.log_lines[2].plain == "third row"
    assert [line.plain for line in _visible_log_lines(state)] == ["second row", "third row"]


def test_normal_mode_log_line_matches_tui_live_log_format() -> None:
    record = logging.LogRecord(
        name="code_auditor.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=0,
        msg="shared format %s",
        args=("message",),
        exc_info=None,
    )
    record.created = 1_700_000_000.0

    state = TUIState()
    _TUILogHandler(state).emit(record)

    console = logger_module.Console(record=True, force_terminal=False, color_system=None)
    logger_module._ConsoleLogHandler(console).emit(record)

    assert console.export_text(styles=False).strip() == state.log_lines[0].plain


def test_log_formatter_includes_exception_traceback() -> None:
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        record = logging.LogRecord(
            name="code_auditor.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=0,
            msg="operation failed",
            args=(),
            exc_info=sys.exc_info(),
        )

    text = logger_module.format_log_record(record).plain

    assert "operation failed" in text
    assert "Traceback" in text
    assert "RuntimeError: boom" in text


def test_tui_log_panel_uses_scrollbar_when_history_exceeds_visible_rows() -> None:
    state = TUIState(max_log_lines=2)
    for index in range(3):
        state.log_lines.append(Text(f"message {index}"))

    panel = _make_log_panel(state)

    assert isinstance(panel.renderable, Table)


def test_tui_log_panel_can_render_scrolled_history() -> None:
    state = TUIState(max_log_lines=2)
    state.log_scroll_offset = 2
    for index in range(5):
        state.log_lines.append(Text(f"message {index}"))

    panel = _make_log_panel(state)
    console = logger_module.Console(record=True, force_terminal=False, color_system=None, width=120)
    console.print(panel)
    rendered = console.export_text(styles=False)

    assert "message 1" in rendered
    assert "message 2" in rendered
    assert "message 4" not in rendered


def test_tui_page_up_scrolls_live_log_panel() -> None:
    manager = TUIManager()
    manager._state.max_log_lines = 2
    manager._state.log_scroll_offset = 0
    for index in range(5):
        manager._state.log_lines.append(Text(f"message {index}"))

    prefix = manager._handle_keyboard_char("\x1b", prefix=False)
    prefix = manager._handle_keyboard_char("[", prefix=prefix)
    prefix = manager._handle_keyboard_char("5", prefix=prefix)
    prefix = manager._handle_keyboard_char("~", prefix=prefix)

    assert prefix is False
    assert manager._state.log_scroll_offset == 2


def test_tui_mouse_wheel_scrolls_live_log_panel() -> None:
    manager = TUIManager()
    manager._console = logger_module.Console(width=80, height=30)
    manager._state.max_log_lines = 2
    for index in range(5):
        manager._state.log_lines.append(Text(f"message {index}"))

    prefix: bool | str = False
    for ch in "\x1b[<64;78;25M":
        prefix = manager._handle_keyboard_char(ch, prefix=prefix)

    assert prefix is False
    assert manager._state.log_scroll_offset == 1

    for ch in "\x1b[<65;78;25M":
        prefix = manager._handle_keyboard_char(ch, prefix=prefix)

    assert prefix is False
    assert manager._state.log_scroll_offset == 0


def test_tui_mouse_click_on_log_scrollbar_jumps_history_position() -> None:
    manager = TUIManager()
    manager._console = logger_module.Console(width=80, height=30)
    manager._state.max_log_lines = 4
    for index in range(20):
        manager._state.log_lines.append(Text(f"message {index}"))

    prefix: bool | str = False
    for ch in "\x1b[<0;78;25M":
        prefix = manager._handle_keyboard_char(ch, prefix=prefix)

    assert prefix is False
    assert manager._state.log_scroll_offset == 16


def test_tui_start_replaces_normal_console_log_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    root_logger = logging.getLogger("code_auditor")
    root_logger.handlers.clear()
    logger_module.configure_logging("INFO")
    manager = TUIManager()

    monkeypatch.setattr(manager, "_start_live", lambda: None)
    monkeypatch.setattr(manager, "_start_keyboard_listener", lambda: None)

    try:
        manager.start()

        assert any(isinstance(handler, _TUILogHandler) for handler in root_logger.handlers)
        assert not any(isinstance(handler, logger_module._ConsoleLogHandler) for handler in root_logger.handlers)
    finally:
        manager.stop()


def test_tui_refresh_limits_live_log_to_available_panel_rows() -> None:
    class FakeLive:
        def update(self, _renderable) -> None:  # type: ignore[no-untyped-def]
            pass

    manager = TUIManager()
    manager._console = logger_module.Console(width=80, height=30)
    manager._live = FakeLive()  # type: ignore[assignment]
    manager._state.max_log_lines = 40
    for index in range(20):
        manager._state.log_lines.append(Text(f"message {index}"))

    _, top, _, bottom = manager._log_panel_content_bounds()
    expected_visible_rows = max(1, bottom - top + 1)

    manager._refresh()

    assert manager._state.max_log_lines == expected_visible_rows
    assert [line.plain for line in _visible_log_lines(manager._state)] == [
        f"message {index}" for index in range(20 - expected_visible_rows, 20)
    ]


def test_tui_wait_for_exit_returns_without_keyboard_listener() -> None:
    manager = TUIManager()
    worker = threading.Thread(target=manager.wait_for_exit)

    worker.start()
    worker.join(timeout=0.2)
    try:
        assert not worker.is_alive()
    finally:
        manager._stop_keyboard.set()
        worker.join(timeout=1.0)


@pytest.mark.parametrize("key", ["q"])
def test_tui_exit_key_requests_exit(key: str) -> None:
    manager = TUIManager()

    prefix = manager._handle_keyboard_char(key, prefix=False)

    assert prefix is False
    assert manager._exit_requested is True
    assert manager._stop_keyboard.is_set()


def test_tui_ctrl_x_a_does_not_switch_modes() -> None:
    manager = TUIManager()

    prefix = manager._handle_keyboard_char("\x18", prefix=False)

    assert prefix is False
    assert manager._exit_requested is False


def test_tui_ctrl_c_interrupts_main_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = TUIManager()
    interrupted = False

    def fake_interrupt_main() -> None:
        nonlocal interrupted
        interrupted = True

    monkeypatch.setattr(manager, "_interrupt_main", fake_interrupt_main)

    manager._handle_keyboard_char("\x03", prefix=False)

    assert interrupted is True
