"""Remote control bridge.

A read/respond bridge so Dave can talk to the fleet from his phone over
Telegram or Discord without exposing the local network. The bridge is
deliberately minimal:

  - polling-based (no inbound webhook required)
  - tool-registry-driven (every command is a registered tool)
  - rate-limited (default 1 call / 2 seconds per chat)
  - allow-list scoped (only configured chat IDs can drive the fleet)
  - graceful when offline (works fully without Telegram/Discord configured —
    you can run in "echo" mode against a local stdin loop for testing)

Telegram is the primary because Hermes Agent uses it as default. Discord is a
webhook + slash-command target (one-way notify is already covered by
``notifications.notifier``; this module adds the *control* direction).

Note: this module exposes the orchestration. The actual commands (slice,
dispatch, queue add, etc.) come from the tool registry. Connecting them is
done by the supervisor at startup.
"""

from __future__ import annotations

import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import httpx

from hermes3d.core.agents.tool_registry import ToolRegistry, tool_registry


@dataclass
class RemoteCommand:
    """One inbound command from a remote channel."""

    chat_id: str
    user: str
    text: str
    received_at: float


@dataclass
class RemoteResponse:
    """One outbound response from the bridge."""

    chat_id: str
    text: str
    parse_mode: str | None = None


@dataclass
class RemoteControlConfig:
    telegram_bot_token: str | None = None
    telegram_allowlist: tuple[str, ...] = ()
    discord_webhook_url: str | None = None
    rate_limit_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> "RemoteControlConfig":
        token = os.getenv("HERMES3D_TELEGRAM_BOT_TOKEN")
        allowlist_raw = os.getenv("HERMES3D_TELEGRAM_ALLOWLIST", "")
        allowlist = tuple(
            x.strip() for x in allowlist_raw.split(",") if x.strip()
        )
        return cls(
            telegram_bot_token=token,
            telegram_allowlist=allowlist,
            discord_webhook_url=os.getenv("HERMES3D_DISCORD_CONTROL_WEBHOOK"),
            rate_limit_seconds=float(os.getenv("HERMES3D_REMOTE_RATE_LIMIT", "2")),
        )


@dataclass
class _RateLimiter:
    window_seconds: float
    history: dict[str, deque[float]] = field(default_factory=dict)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self.history.setdefault(key, deque(maxlen=10))
        if bucket and now - bucket[-1] < self.window_seconds:
            return False
        bucket.append(now)
        return True


class CommandRouter:
    """Parses inbound text into tool calls and produces a response.

    Supported syntax:
      /<tool_name> [k=v ...]
      help
      tools
      <tool_name> [k=v ...]
    """

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self._registry = registry or tool_registry

    def handle(self, command: RemoteCommand) -> RemoteResponse:
        text = command.text.strip()
        if not text:
            return self._response(command, "Empty command. Try `help`.")
        if text.lower() in ("help", "/help", "?"):
            return self._help_response(command)
        if text.lower() in ("tools", "/tools"):
            return self._tools_response(command)

        if text.startswith("/"):
            text = text[1:]
        parts = text.split()
        tool_name = parts[0]
        kwargs: dict[str, Any] = {}
        for kv in parts[1:]:
            if "=" not in kv:
                return self._response(
                    command,
                    f"Bad argument {kv!r}: expected key=value form.",
                )
            k, v = kv.split("=", 1)
            kwargs[k] = self._coerce(v)

        if tool_name not in self._registry:
            return self._response(
                command,
                f"Unknown tool {tool_name!r}. Try `tools` to list.",
            )

        try:
            result = self._registry.call(tool_name, **kwargs)
        except Exception as exc:  # surface real errors back to the operator
            return self._response(command, f"❌ {tool_name} failed: {exc}")

        return self._response(command, f"✅ {tool_name} → {self._render_result(result)}")

    @staticmethod
    def _coerce(value: str) -> Any:
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def _help_response(self, command: RemoteCommand) -> RemoteResponse:
        msg = (
            "Hermes3D-OS remote control:\n"
            "• `tools` — list available tools\n"
            "• `<tool> k=v ...` — invoke a tool\n"
            "• `help` — this message"
        )
        return self._response(command, msg)

    def _tools_response(self, command: RemoteCommand) -> RemoteResponse:
        lines = ["Available tools:"]
        for tool in self._registry.all():
            lines.append(f"• `{tool.name}` ({tool.category}) — {tool.description}")
        return self._response(command, "\n".join(lines))

    @staticmethod
    def _response(command: RemoteCommand, text: str) -> RemoteResponse:
        return RemoteResponse(chat_id=command.chat_id, text=text, parse_mode="Markdown")

    @staticmethod
    def _render_result(result: Any) -> str:
        if result is None:
            return "ok"
        s = str(result)
        return s if len(s) <= 1500 else s[:1500] + "…"


class TelegramTransport:
    """Long-poll Telegram getUpdates -> sendMessage transport.

    Used in a poll loop. Returns ``[]`` if no token is configured.
    """

    def __init__(self, config: RemoteControlConfig) -> None:
        self._config = config
        self._offset: int | None = None
        self._enabled = bool(config.telegram_bot_token)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def fetch(self, *, timeout_seconds: float = 1.0) -> list[RemoteCommand]:  # pragma: no cover - network
        if not self._enabled:
            return []
        params: dict[str, Any] = {"timeout": int(timeout_seconds)}
        if self._offset is not None:
            params["offset"] = self._offset
        url = f"https://api.telegram.org/bot{self._config.telegram_bot_token}/getUpdates"
        with httpx.Client(timeout=timeout_seconds + 5.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        commands: list[RemoteCommand] = []
        for update in data.get("result", []):
            self._offset = max(self._offset or 0, update["update_id"] + 1)
            msg = update.get("message") or update.get("edited_message")
            if not msg:
                continue
            chat_id = str(msg["chat"]["id"])
            if (
                self._config.telegram_allowlist
                and chat_id not in self._config.telegram_allowlist
            ):
                continue
            commands.append(
                RemoteCommand(
                    chat_id=chat_id,
                    user=msg.get("from", {}).get("username", "anon"),
                    text=msg.get("text", "") or "",
                    received_at=time.time(),
                )
            )
        return commands

    def send(self, response: RemoteResponse) -> None:  # pragma: no cover - network
        if not self._enabled:
            return
        url = f"https://api.telegram.org/bot{self._config.telegram_bot_token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": response.chat_id,
            "text": response.text,
        }
        if response.parse_mode:
            payload["parse_mode"] = response.parse_mode
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(url, json=payload)
        except httpx.HTTPError:
            pass  # best-effort, don't crash the bridge


class DiscordTransport:
    """One-way Discord webhook for sending command results.

    Discord doesn't have inbound polling without a full bot user, which Dave
    doesn't want; for inbound, use Telegram. This transport just reports.
    """

    def __init__(self, config: RemoteControlConfig) -> None:
        self._config = config
        self._enabled = bool(config.discord_webhook_url)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def send(self, response: RemoteResponse) -> None:  # pragma: no cover - network
        if not self._enabled:
            return
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(
                    self._config.discord_webhook_url,
                    json={"content": response.text[:1900]},
                )
        except httpx.HTTPError:
            pass


class RemoteControlBridge:
    """Glues transports + router + rate limiting together.

    Designed to be invoked from the supervisor's ticker. Each ``tick()`` call
    drains pending commands and emits responses.
    """

    def __init__(
        self,
        *,
        config: RemoteControlConfig | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.config = config or RemoteControlConfig.from_env()
        self.router = CommandRouter(registry)
        self.telegram = TelegramTransport(self.config)
        self.discord = DiscordTransport(self.config)
        self._limiter = _RateLimiter(window_seconds=self.config.rate_limit_seconds)

    @property
    def configured(self) -> bool:
        return self.telegram.enabled or self.discord.enabled

    def handle_text(self, *, chat_id: str, user: str, text: str) -> RemoteResponse:
        """Synchronous helper for unit tests / stdin loop / API-driven control."""
        cmd = RemoteCommand(chat_id=chat_id, user=user, text=text, received_at=time.time())
        if not self._limiter.allow(chat_id):
            return RemoteResponse(
                chat_id=chat_id,
                text="⚠ rate limited — slow down.",
            )
        return self.router.handle(cmd)

    def tick(self) -> list[RemoteResponse]:  # pragma: no cover - network heavy
        """Poll Telegram once and dispatch any commands."""
        responses: list[RemoteResponse] = []
        if not self.telegram.enabled:
            return responses
        for cmd in self.telegram.fetch():
            if not self._limiter.allow(cmd.chat_id):
                resp = RemoteResponse(
                    chat_id=cmd.chat_id,
                    text="⚠ rate limited — slow down.",
                )
            else:
                resp = self.router.handle(cmd)
            self.telegram.send(resp)
            responses.append(resp)
        return responses


__all__ = [
    "CommandRouter",
    "DiscordTransport",
    "RemoteCommand",
    "RemoteControlBridge",
    "RemoteControlConfig",
    "RemoteResponse",
    "TelegramTransport",
]
