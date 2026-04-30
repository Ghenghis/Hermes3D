"""Unit tests for the remote control bridge (Telegram + Discord).

No real network calls are made -- the HTTP transports are patched.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from hermes3d.core.agents.tool_registry import ToolRegistry, ToolSpec
from hermes3d.core.integrations.remote_control import (
    COMMAND_TABLE,
    CommandRouter,
    DiscordTransport,
    RemoteCommand,
    RemoteControlBridge,
    RemoteControlConfig,
    TelegramTransport,
)


# --- Test fixtures -----------------------------------------------------------


def _make_registry() -> ToolRegistry:
    """Build a fresh registry with stub tools matching the COMMAND_TABLE."""
    reg = ToolRegistry()

    def fleet_status() -> dict[str, str]:
        return {"printers": "12 online"}

    def queue_list() -> list[str]:
        return ["job-1", "job-2"]

    def spool_list() -> list[str]:
        return ["PLA-black", "PETG-clear"]

    def dispatch_print(stl_path: str) -> str:
        return f"dispatched {stl_path}"

    def cancel_job(job_id: str) -> str:
        return f"cancelled {job_id}"

    def fleet_health() -> dict[str, str]:
        return {"status": "green"}

    schema = {"type": "object", "properties": {}}
    schema_with_path = {
        "type": "object",
        "properties": {"stl_path": {"type": "string"}},
        "required": ["stl_path"],
    }
    schema_with_id = {
        "type": "object",
        "properties": {"job_id": {"type": "string"}},
        "required": ["job_id"],
    }

    reg.register(ToolSpec("fleet_status", "fleet status", schema, fleet_status))
    reg.register(ToolSpec("queue_list", "queue list", schema, queue_list))
    reg.register(ToolSpec("spool_list", "spool list", schema, spool_list))
    reg.register(ToolSpec("dispatch_print", "dispatch", schema_with_path, dispatch_print))
    reg.register(ToolSpec("cancel_job", "cancel", schema_with_id, cancel_job))
    reg.register(ToolSpec("fleet_health", "health", schema, fleet_health))
    return reg


def _cmd(text: str, chat_id: str = "42", user: str = "dave") -> RemoteCommand:
    return RemoteCommand(chat_id=chat_id, user=user, text=text, received_at=time.time())


# --- Command parsing ---------------------------------------------------------


class TestCommandParsing:
    def test_parse_status(self) -> None:
        router = CommandRouter(_make_registry())
        assert router.parse("/status") == ("/status", [])

    def test_parse_queue_with_extra_whitespace(self) -> None:
        router = CommandRouter(_make_registry())
        assert router.parse("   /queue   ") == ("/queue", [])

    def test_parse_dispatch_with_argument(self) -> None:
        router = CommandRouter(_make_registry())
        assert router.parse("/dispatch /tmp/foo.stl") == (
            "/dispatch",
            ["/tmp/foo.stl"],
        )

    def test_parse_cancel_with_id(self) -> None:
        router = CommandRouter(_make_registry())
        assert router.parse("/cancel job-123") == ("/cancel", ["job-123"])

    def test_parse_help_alias_without_slash(self) -> None:
        router = CommandRouter(_make_registry())
        head, args = router.parse("help")
        assert head == "/help"
        assert args == []

    def test_parse_returns_none_on_empty(self) -> None:
        router = CommandRouter(_make_registry())
        assert router.parse("") is None
        assert router.parse("   ") is None

    def test_parse_returns_none_on_unbalanced_quotes(self) -> None:
        router = CommandRouter(_make_registry())
        assert router.parse('/dispatch "unbalanced') is None


# --- Dispatch to mock tools --------------------------------------------------


class TestDispatch:
    def test_status_dispatches_to_tool(self) -> None:
        registry = _make_registry()
        router = CommandRouter(registry)
        resp = router.handle(_cmd("/status"))
        assert "fleet_status" not in resp.text  # we render the result, not name
        assert "12 online" in resp.text
        assert resp.text.startswith("OK ")

    def test_dispatch_with_arg(self) -> None:
        registry = _make_registry()
        router = CommandRouter(registry)
        resp = router.handle(_cmd("/dispatch /tmp/widget.stl"))
        assert "dispatched /tmp/widget.stl" in resp.text

    def test_cancel_with_arg(self) -> None:
        registry = _make_registry()
        router = CommandRouter(registry)
        resp = router.handle(_cmd("/cancel job-42"))
        assert "cancelled job-42" in resp.text

    def test_dispatch_uses_mock_tool(self) -> None:
        registry = ToolRegistry()
        mock_handler = MagicMock(return_value="mocked!")
        registry.register(
            ToolSpec(
                "fleet_status",
                "stub",
                {"type": "object", "properties": {}},
                mock_handler,
            )
        )
        router = CommandRouter(registry)
        resp = router.handle(_cmd("/status"))
        mock_handler.assert_called_once()
        assert "mocked!" in resp.text

    def test_tool_exception_is_reported(self) -> None:
        registry = ToolRegistry()

        def boom() -> None:
            raise RuntimeError("kaboom")

        registry.register(
            ToolSpec(
                "fleet_status",
                "boom",
                {"type": "object", "properties": {}},
                boom,
            )
        )
        router = CommandRouter(registry)
        resp = router.handle(_cmd("/status"))
        assert "failed" in resp.text.lower()
        assert "kaboom" in resp.text


# --- Help / unknown / malformed ----------------------------------------------


class TestHelpAndErrors:
    def test_unknown_command_returns_help(self) -> None:
        router = CommandRouter(_make_registry())
        resp = router.handle(_cmd("/banana"))
        # Either the command-table miss path or the dynamic-tool miss path.
        assert "Unknown" in resp.text
        assert "/help" in resp.text or "help" in resp.text.lower()

    def test_help_command_lists_all_commands(self) -> None:
        router = CommandRouter(_make_registry())
        resp = router.handle(_cmd("/help"))
        for spec in COMMAND_TABLE:
            assert spec.command in resp.text
        assert "/help" in resp.text

    def test_malformed_input_returns_error(self) -> None:
        router = CommandRouter(_make_registry())
        resp = router.handle(_cmd('/dispatch "unclosed'))
        assert "Malformed" in resp.text or "could not parse" in resp.text.lower()

    def test_empty_input_returns_error(self) -> None:
        router = CommandRouter(_make_registry())
        resp = router.handle(_cmd(""))
        assert "Malformed" in resp.text or "could not parse" in resp.text.lower()

    def test_missing_positional_argument(self) -> None:
        router = CommandRouter(_make_registry())
        resp = router.handle(_cmd("/dispatch"))
        assert "Missing argument" in resp.text
        assert "stl_path" in resp.text

    def test_unregistered_tool_reports_unavailable(self) -> None:
        registry = ToolRegistry()  # empty: nothing registered
        router = CommandRouter(registry)
        resp = router.handle(_cmd("/status"))
        assert "not registered" in resp.text


# --- Telegram transport (HTTP patched) ---------------------------------------


class TestTelegramTransport:
    def test_disabled_when_no_token(self) -> None:
        cfg = RemoteControlConfig(telegram_bot_token=None)
        t = TelegramTransport(cfg)
        assert t.enabled is False
        assert t.fetch() == []

    def test_fetch_parses_updates(self) -> None:
        cfg = RemoteControlConfig(telegram_bot_token="TKN")
        fake_get = MagicMock(
            return_value={
                "result": [
                    {
                        "update_id": 1,
                        "message": {
                            "chat": {"id": 99},
                            "from": {"username": "dave"},
                            "text": "/status",
                        },
                    }
                ]
            }
        )
        t = TelegramTransport(cfg, http_get=fake_get, http_post=MagicMock())
        cmds = t.fetch()
        assert len(cmds) == 1
        assert cmds[0].chat_id == "99"
        assert cmds[0].text == "/status"
        # offset advanced
        t.fetch()
        called_url = fake_get.call_args_list[-1][0][0]
        assert "offset=2" in called_url

    def test_fetch_respects_allowlist(self) -> None:
        cfg = RemoteControlConfig(
            telegram_bot_token="TKN",
            telegram_allowlist=("777",),
        )
        fake_get = MagicMock(
            return_value={
                "result": [
                    {
                        "update_id": 1,
                        "message": {
                            "chat": {"id": 99},
                            "from": {"username": "intruder"},
                            "text": "/status",
                        },
                    }
                ]
            }
        )
        t = TelegramTransport(cfg, http_get=fake_get, http_post=MagicMock())
        assert t.fetch() == []

    def test_send_posts_message(self) -> None:
        cfg = RemoteControlConfig(telegram_bot_token="TKN")
        fake_post = MagicMock(return_value=None)
        t = TelegramTransport(cfg, http_get=MagicMock(), http_post=fake_post)
        from hermes3d.core.integrations.remote_control import RemoteResponse

        t.send(RemoteResponse(chat_id="99", text="hi", parse_mode="Markdown"))
        fake_post.assert_called_once()
        url, payload = fake_post.call_args[0]
        assert "sendMessage" in url
        assert payload == {"chat_id": "99", "text": "hi", "parse_mode": "Markdown"}

    def test_send_no_op_when_disabled(self) -> None:
        cfg = RemoteControlConfig(telegram_bot_token=None)
        fake_post = MagicMock()
        t = TelegramTransport(cfg, http_get=MagicMock(), http_post=fake_post)
        from hermes3d.core.integrations.remote_control import RemoteResponse

        t.send(RemoteResponse(chat_id="99", text="hi"))
        fake_post.assert_not_called()

    def test_fetch_handles_network_error(self) -> None:
        import urllib.error

        cfg = RemoteControlConfig(telegram_bot_token="TKN")
        fake_get = MagicMock(side_effect=urllib.error.URLError("offline"))
        t = TelegramTransport(cfg, http_get=fake_get, http_post=MagicMock())
        assert t.fetch() == []


# --- Discord webhook transport ------------------------------------------------


class TestDiscordTransport:
    def test_disabled_without_webhook(self) -> None:
        cfg = RemoteControlConfig(discord_webhook_url=None)
        d = DiscordTransport(cfg)
        assert d.enabled is False

    def test_send_posts_to_webhook(self) -> None:
        cfg = RemoteControlConfig(discord_webhook_url="https://discord.example/webhooks/abc")
        fake_post = MagicMock(return_value=None)
        d = DiscordTransport(cfg, http_post=fake_post)
        from hermes3d.core.integrations.remote_control import RemoteResponse

        d.send(RemoteResponse(chat_id="x", text="result"))
        fake_post.assert_called_once()
        url, payload = fake_post.call_args[0]
        assert url == "https://discord.example/webhooks/abc"
        assert payload == {"content": "result"}

    def test_send_truncates_long_content(self) -> None:
        cfg = RemoteControlConfig(discord_webhook_url="https://discord.example/webhooks/abc")
        fake_post = MagicMock(return_value=None)
        d = DiscordTransport(cfg, http_post=fake_post)
        from hermes3d.core.integrations.remote_control import RemoteResponse

        d.send(RemoteResponse(chat_id="x", text="A" * 5000))
        payload = fake_post.call_args[0][1]
        assert len(payload["content"]) <= 1900


# --- Bridge integration (everything wired) -----------------------------------


class TestRemoteControlBridge:
    def test_handle_text_dispatches_through_router(self) -> None:
        registry = _make_registry()
        cfg = RemoteControlConfig(rate_limit_seconds=0.0)
        bridge = RemoteControlBridge(config=cfg, registry=registry)
        resp = bridge.handle_text(chat_id="1", user="dave", text="/status")
        assert "12 online" in resp.text

    def test_rate_limit_kicks_in(self) -> None:
        registry = _make_registry()
        cfg = RemoteControlConfig(rate_limit_seconds=60.0)
        bridge = RemoteControlBridge(config=cfg, registry=registry)
        first = bridge.handle_text(chat_id="1", user="dave", text="/status")
        second = bridge.handle_text(chat_id="1", user="dave", text="/status")
        assert "12 online" in first.text
        assert "rate limited" in second.text

    def test_tick_dispatches_and_sends_to_both_channels(self) -> None:
        registry = _make_registry()
        cfg = RemoteControlConfig(
            telegram_bot_token="TKN",
            discord_webhook_url="https://discord.example/wh",
            rate_limit_seconds=0.0,
        )
        fake_get = MagicMock(
            return_value={
                "result": [
                    {
                        "update_id": 7,
                        "message": {
                            "chat": {"id": 1},
                            "from": {"username": "dave"},
                            "text": "/status",
                        },
                    }
                ]
            }
        )
        fake_post = MagicMock(return_value=None)
        telegram = TelegramTransport(cfg, http_get=fake_get, http_post=fake_post)
        discord = DiscordTransport(cfg, http_post=fake_post)
        bridge = RemoteControlBridge(
            config=cfg,
            registry=registry,
            telegram=telegram,
            discord=discord,
        )
        responses = bridge.tick()
        assert len(responses) == 1
        assert "12 online" in responses[0].text
        # Two POSTs: one to telegram sendMessage, one to discord webhook.
        assert fake_post.call_count == 2

    def test_from_env_reads_discord_webhook(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HERMES3D_DISCORD_WEBHOOK", "https://d.example/wh")
        monkeypatch.delenv("HERMES3D_DISCORD_CONTROL_WEBHOOK", raising=False)
        monkeypatch.delenv("HERMES3D_TELEGRAM_BOT_TOKEN", raising=False)
        cfg = RemoteControlConfig.from_env()
        assert cfg.discord_webhook_url == "https://d.example/wh"


# --- HTTP helpers patched at module scope (sanity) ---------------------------


def test_telegram_send_with_real_module_patched() -> None:
    """Confirm stdlib urllib.request is the only network surface (no httpx)."""
    import hermes3d.core.integrations.remote_control as rc

    # urllib.request is imported by the module; httpx must NOT be.
    import sys

    assert "hermes3d.core.integrations.remote_control" in sys.modules
    src = rc.__file__
    with open(src, encoding="utf-8") as fh:
        body = fh.read()
    assert "import httpx" not in body, "transport should not depend on httpx"
    assert "urllib.request" in body, "transport should use stdlib urllib"

    # And confirm urlopen is the actual call site by patching it.
    cfg = RemoteControlConfig(telegram_bot_token="TKN")
    t = TelegramTransport(cfg)
    from hermes3d.core.integrations.remote_control import RemoteResponse

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b""
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        t.send(RemoteResponse(chat_id="1", text="hello"))
        mock_urlopen.assert_called_once()
