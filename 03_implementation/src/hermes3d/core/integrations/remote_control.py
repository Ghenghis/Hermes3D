"""Remote control bridge.

A read/respond bridge so Dave can talk to the fleet from his phone over
Telegram or Discord without exposing the local network. The bridge is
deliberately minimal:

  - polling-based for Telegram (no inbound webhook required)
  - finite command table mapping textual commands -> registered tools
  - rate-limited (default 1 call / 2 seconds per chat)
  - allow-list scoped (only configured chat IDs can drive the fleet)
  - graceful when offline (works fully without Telegram/Discord configured)

Telegram is the primary inbound channel because Hermes Agent uses it as
default. Discord is a one-way webhook target (POST result back).

Networking uses stdlib ``urllib.request`` only -- no third-party SDK.
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from hermes3d.core.agents.tool_registry import ToolRegistry, tool_registry

LOG = logging.getLogger(__name__)


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
        allowlist = tuple(x.strip() for x in allowlist_raw.split(",") if x.strip())
        # Per A.7: discord webhook is read from HERMES3D_DISCORD_WEBHOOK.
        # The legacy env var ``HERMES3D_DISCORD_CONTROL_WEBHOOK`` is also
        # accepted as a fallback for compatibility with existing deployments.
        discord_webhook = os.getenv("HERMES3D_DISCORD_WEBHOOK") or os.getenv(
            "HERMES3D_DISCORD_CONTROL_WEBHOOK"
        )
        return cls(
            telegram_bot_token=token,
            telegram_allowlist=allowlist,
            discord_webhook_url=discord_webhook,
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


@dataclass(frozen=True)
class CommandSpec:
    """A finite-table entry: textual command -> tool invocation rule."""

    command: str
    tool_name: str
    description: str
    # Names of positional arguments to pull off the message text, in order.
    positional_args: tuple[str, ...] = ()


# Finite command table. Maps the user-facing slash commands to tools in the
# registry. Adding a new remote command means adding a row here -- no parsing
# magic, no reflection.
COMMAND_TABLE: tuple[CommandSpec, ...] = (
    CommandSpec("/status", "fleet_status", "Show printer + queue status."),
    CommandSpec("/queue", "queue_list", "List current job queue."),
    CommandSpec("/spools", "spool_list", "List loaded spools."),
    CommandSpec(
        "/dispatch",
        "dispatch_print",
        "Dispatch an STL: /dispatch <stl-path>",
        positional_args=("stl_path",),
    ),
    CommandSpec(
        "/cancel",
        "cancel_job",
        "Cancel a running job: /cancel <job-id>",
        positional_args=("job_id",),
    ),
    CommandSpec("/health", "fleet_health", "Aggregate fleet health probe."),
)


def _build_help_text() -> str:
    lines = ["Hermes3D-OS remote control commands:"]
    for spec in COMMAND_TABLE:
        lines.append(f"  {spec.command} - {spec.description}")
    lines.append("  /tools - list all registered tools")
    lines.append("  /help - this message")
    return "\n".join(lines)


class CommandRouter:
    """Parses inbound text into tool calls using a finite command table.

    Supported syntax:
      /<command> [positional args...]
      /help
    """

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        *,
        command_table: tuple[CommandSpec, ...] = COMMAND_TABLE,
    ) -> None:
        self._registry = registry or tool_registry
        self._table: dict[str, CommandSpec] = {spec.command: spec for spec in command_table}

    @property
    def commands(self) -> tuple[str, ...]:
        return tuple(sorted(self._table)) + ("/help",)

    def parse(self, text: str) -> tuple[str, list[str]] | None:
        """Return (command, args) tuple or None if input is malformed.

        ``None`` means the input could not be lexed at all (e.g. unbalanced
        quotes) -- the caller should respond with an error.
        """
        text = (text or "").strip()
        if not text:
            return None
        try:
            tokens = shlex.split(text)
        except ValueError:
            return None
        if not tokens:
            return None
        head = tokens[0]
        # Normalise: accept `status` as `/status`.
        if not head.startswith("/"):
            head = "/" + head
        return head.lower(), tokens[1:]

    def handle(self, command: RemoteCommand) -> RemoteResponse:
        parsed = self.parse(command.text)
        if parsed is None:
            return self._response(
                command,
                "Malformed command (could not parse). Send /help for usage.",
            )
        head, args = parsed
        if head in ("/help", "/?"):
            return self._response(command, _build_help_text())
        if head == "/tools":
            return self._tools_response(command)
        spec = self._table.get(head)
        if spec is not None:
            if len(args) < len(spec.positional_args):
                missing = ", ".join(spec.positional_args[len(args) :])
                return self._response(
                    command,
                    f"Missing argument(s) for {head}: {missing}.\nUsage: {spec.description}",
                )
            kwargs = dict(zip(spec.positional_args, args, strict=False))
            tool_name = spec.tool_name
            if tool_name not in self._registry:
                return self._response(
                    command,
                    f"Tool {tool_name!r} not registered (command {head} unavailable).",
                )
            return self._invoke(command, head, tool_name, kwargs)

        # Fallback: treat ``head`` (without leading slash) as a tool name and
        # parse any remaining args as ``key=value`` pairs. This keeps
        # back-compat with the registry-driven syntax used by older clients.
        tool_name = head[1:]  # strip leading slash from `/foo`
        kwargs: dict[str, Any] = {}
        for kv in args:
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
                f"Unknown tool {tool_name!r}. Try /help to list commands.",
            )
        return self._invoke(command, head, tool_name, kwargs)

    def _invoke(
        self,
        command: RemoteCommand,
        head: str,
        tool_name: str,
        kwargs: dict[str, Any],
    ) -> RemoteResponse:
        try:
            result = self._registry.call(tool_name, **kwargs)
        except Exception as exc:  # surface real errors back to the operator
            LOG.exception("remote command %s failed", head)
            return self._response(command, f"X {head} failed: {exc}")
        return self._response(
            command,
            f"OK {head} -> {self._render_result(result)}",
        )

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

    def _tools_response(self, command: RemoteCommand) -> RemoteResponse:
        lines = ["Available tools:"]
        for tool in self._registry.all():
            lines.append(f"- {tool.name} ({tool.category}) - {tool.description}")
        return self._response(command, "\n".join(lines))

    @staticmethod
    def _response(command: RemoteCommand, text: str) -> RemoteResponse:
        return RemoteResponse(chat_id=command.chat_id, text=text, parse_mode="Markdown")

    @staticmethod
    def _render_result(result: Any) -> str:
        if result is None:
            return "ok"
        s = str(result)
        return s if len(s) <= 1500 else s[:1500] + "..."


# --- HTTP transport primitives (stdlib only) ---------------------------------


def _http_get_json(url: str, *, timeout: float = 10.0) -> dict[str, Any]:
    """GET ``url`` and decode JSON. Raises urllib.error on failure."""
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - trusted https
        body = resp.read()
    return json.loads(body.decode("utf-8"))


def _http_post_json(
    url: str, payload: dict[str, Any], *, timeout: float = 10.0
) -> dict[str, Any] | None:
    """POST a JSON payload to ``url``. Returns parsed JSON if any."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - trusted https
        body = resp.read()
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


class TelegramTransport:
    """Long-poll Telegram getUpdates -> sendMessage transport.

    Uses stdlib ``urllib.request`` to call the Telegram Bot API. Returns
    ``[]`` if no token is configured.
    """

    API_BASE = "https://api.telegram.org"

    def __init__(
        self,
        config: RemoteControlConfig,
        *,
        http_get: Callable[..., dict[str, Any]] = _http_get_json,
        http_post: Callable[..., dict[str, Any] | None] = _http_post_json,
    ) -> None:
        self._config = config
        self._offset: int | None = None
        self._enabled = bool(config.telegram_bot_token)
        self._http_get = http_get
        self._http_post = http_post

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _url(self, method: str) -> str:
        return f"{self.API_BASE}/bot{self._config.telegram_bot_token}/{method}"

    def fetch(self, *, timeout_seconds: float = 1.0) -> list[RemoteCommand]:
        if not self._enabled:
            return []
        params: dict[str, Any] = {"timeout": int(timeout_seconds)}
        if self._offset is not None:
            params["offset"] = self._offset
        url = self._url("getUpdates") + "?" + urllib.parse.urlencode(params)
        try:
            data = self._http_get(url, timeout=timeout_seconds + 5.0)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            LOG.warning("telegram getUpdates failed: %s", exc)
            return []

        commands: list[RemoteCommand] = []
        for update in data.get("result", []):
            self._offset = max(self._offset or 0, update["update_id"] + 1)
            msg = update.get("message") or update.get("edited_message")
            if not msg:
                continue
            chat_id = str(msg["chat"]["id"])
            if self._config.telegram_allowlist and chat_id not in self._config.telegram_allowlist:
                LOG.info("dropping telegram message from non-allowlisted chat %s", chat_id)
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

    def send(self, response: RemoteResponse) -> None:
        if not self._enabled:
            return
        payload: dict[str, Any] = {
            "chat_id": response.chat_id,
            "text": response.text,
        }
        if response.parse_mode:
            payload["parse_mode"] = response.parse_mode
        try:
            self._http_post(self._url("sendMessage"), payload, timeout=10.0)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # Best-effort: don't crash the bridge on transient send failure.
            LOG.warning("telegram sendMessage failed: %s", exc)


class DiscordTransport:
    """One-way Discord webhook for sending command results.

    Discord webhooks accept POSTs of the shape ``{"content": "..."}``. We
    cap content at 1900 chars to stay under Discord's 2000-char limit.
    """

    def __init__(
        self,
        config: RemoteControlConfig,
        *,
        http_post: Callable[..., dict[str, Any] | None] = _http_post_json,
    ) -> None:
        self._config = config
        self._enabled = bool(config.discord_webhook_url)
        self._http_post = http_post

    @property
    def enabled(self) -> bool:
        return self._enabled

    def send(self, response: RemoteResponse) -> None:
        if not self._enabled or not self._config.discord_webhook_url:
            return
        try:
            self._http_post(
                self._config.discord_webhook_url,
                {"content": response.text[:1900]},
                timeout=10.0,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            LOG.warning("discord webhook send failed: %s", exc)


class RemoteControlBridge:
    """Glues transports + router + rate limiting together."""

    def __init__(
        self,
        *,
        config: RemoteControlConfig | None = None,
        registry: ToolRegistry | None = None,
        telegram: TelegramTransport | None = None,
        discord: DiscordTransport | None = None,
    ) -> None:
        self.config = config or RemoteControlConfig.from_env()
        self.router = CommandRouter(registry)
        self.telegram = telegram if telegram is not None else TelegramTransport(self.config)
        self.discord = discord if discord is not None else DiscordTransport(self.config)
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
                text="rate limited - slow down.",
            )
        return self.router.handle(cmd)

    def tick(self) -> list[RemoteResponse]:
        """Poll Telegram once and dispatch any commands.

        Each response is also mirrored to Discord (if configured) for
        cross-channel auditability.
        """
        responses: list[RemoteResponse] = []
        if not self.telegram.enabled:
            return responses
        for cmd in self.telegram.fetch():
            if not self._limiter.allow(cmd.chat_id):
                resp = RemoteResponse(
                    chat_id=cmd.chat_id,
                    text="rate limited - slow down.",
                )
            else:
                resp = self.router.handle(cmd)
            try:
                self.telegram.send(resp)
            except Exception:
                LOG.exception("telegram send raised")
            if self.discord.enabled:
                try:
                    self.discord.send(resp)
                except Exception:
                    LOG.exception("discord send raised")
            responses.append(resp)
        return responses


__all__ = [
    "COMMAND_TABLE",
    "CommandRouter",
    "CommandSpec",
    "DiscordTransport",
    "RemoteCommand",
    "RemoteControlBridge",
    "RemoteControlConfig",
    "RemoteResponse",
    "TelegramTransport",
]
