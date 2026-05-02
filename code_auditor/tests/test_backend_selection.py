from __future__ import annotations

import asyncio
import logging
import sys

import pytest

from code_auditor import __main__ as main_module
from code_auditor import agent
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
    capsys: pytest.CaptureFixture[str],
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

    main_module.main()

    assert f"Loaded wiki knowledge base: {wiki.resolve()}" in capsys.readouterr().err


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
