"""Structured logging helper for Crowd Control melee bots."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from melee.gamestate import GameState

RECENT_LOG_LIMIT = 20
LOG_MESSAGE_BYTE_LIMIT = 16 * 1024
_LEVEL_NAMES = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}


@dataclass(frozen=True)
class BotLogEntry:
    """One deduplicated status line retained for stream overlays."""

    message: str
    level: int
    repetition_count: int = 0


class BotLogger:
    """Logger wrapper that deduplicates bot status lines and tracks recent messages.

    Each emit method requires a ``GameState`` so the underlying logger receives a
    ``frame=…`` prefix. That prefix is omitted from buffered overlay entries.
    """

    def __init__(self, bot_name: str) -> None:
        self._bot_name = bot_name
        self._logger = logging.getLogger(f"crowd_control.bot.{bot_name}")
        self._recent_logs: list[BotLogEntry] = []
        self._match_logs: list[BotLogEntry] = []
        self._last_heartbeat_frame = -9999

    @property
    def bot_name(self) -> str:
        """Logical profile name from the bot file metadata."""
        return self._bot_name

    @property
    def recent_logs(self) -> tuple[BotLogEntry, ...]:
        """Up to :data:`RECENT_LOG_LIMIT` unique messages, oldest first."""
        return tuple(self._recent_logs)

    @property
    def match_logs(self) -> tuple[BotLogEntry, ...]:
        """All deduplicated messages emitted since the last match reset."""
        return tuple(self._match_logs)

    def match_log_text(self) -> str:
        """Render the complete per-match bot log for persistence."""
        return "".join(_render_entry(entry) for entry in self._match_logs)

    @property
    def last_log_message(self) -> str | None:
        """Most recent unique log message, without the frame prefix."""
        if not self._recent_logs:
            return None
        return self._recent_logs[-1].message

    @property
    def last_log_repetition_count(self) -> int:
        """How many additional times :attr:`last_log_message` has been emitted."""
        if not self._recent_logs:
            return 0
        return self._recent_logs[-1].repetition_count

    @property
    def last_log_level(self) -> int | None:
        """Logging level of :attr:`last_log_message`, or ``None`` when empty."""
        if not self._recent_logs:
            return None
        return self._recent_logs[-1].level

    def clear_last_log(self) -> None:
        """Clear buffered messages and deduplication state."""
        self._recent_logs.clear()

    def reset(self) -> None:
        """Reset buffered log state and heartbeat throttling (call at match start)."""
        self.clear_last_log()
        self._match_logs.clear()
        self._last_heartbeat_frame = -9999

    def maybe_heartbeat(
        self,
        game_state: GameState,
        detail: str,
        *,
        interval: int = 60,
    ) -> None:
        """Emit a throttled DEBUG status line for steady states."""
        if game_state.frame - self._last_heartbeat_frame < interval:
            return
        self._last_heartbeat_frame = game_state.frame
        self.debug(game_state, detail)

    def isEnabledFor(self, level: int) -> bool:
        return self._logger.isEnabledFor(level)

    def getEffectiveLevel(self) -> int:
        return self._logger.getEffectiveLevel()

    def debug(
        self,
        game_state: GameState,
        msg: object,
        *args: object,
        **kwargs: Any,
    ) -> None:
        self.log(logging.DEBUG, game_state, msg, *args, **kwargs)

    def info(
        self,
        game_state: GameState,
        msg: object,
        *args: object,
        **kwargs: Any,
    ) -> None:
        self.log(logging.INFO, game_state, msg, *args, **kwargs)

    def warning(
        self,
        game_state: GameState,
        msg: object,
        *args: object,
        **kwargs: Any,
    ) -> None:
        self.log(logging.WARNING, game_state, msg, *args, **kwargs)

    def error(
        self,
        game_state: GameState,
        msg: object,
        *args: object,
        **kwargs: Any,
    ) -> None:
        self.log(logging.ERROR, game_state, msg, *args, **kwargs)

    def critical(
        self,
        game_state: GameState,
        msg: object,
        *args: object,
        **kwargs: Any,
    ) -> None:
        self.log(logging.CRITICAL, game_state, msg, *args, **kwargs)

    def exception(
        self,
        game_state: GameState,
        msg: object,
        *args: object,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("exc_info", True)
        self.log(logging.ERROR, game_state, msg, *args, **kwargs)

    def log(
        self,
        level: int,
        game_state: GameState,
        msg: object,
        *args: object,
        **kwargs: Any,
    ) -> None:
        if not self._logger.isEnabledFor(level):
            return
        message = _format_message(msg, args)
        recent_message = _truncate_utf8(message, LOG_MESSAGE_BYTE_LIMIT)
        recent_duplicate = bool(
            self._recent_logs and self._recent_logs[-1].message == recent_message
        )
        if recent_duplicate:
            last = self._recent_logs[-1]
            self._recent_logs[-1] = BotLogEntry(
                message=last.message,
                level=last.level,
                repetition_count=last.repetition_count + 1,
            )
        else:
            self._recent_logs.append(BotLogEntry(message=recent_message, level=level))
            if len(self._recent_logs) > RECENT_LOG_LIMIT:
                del self._recent_logs[0]

        if self._match_logs and self._match_logs[-1].message == message:
            match_last = self._match_logs[-1]
            self._match_logs[-1] = BotLogEntry(
                message=match_last.message,
                level=match_last.level,
                repetition_count=match_last.repetition_count + 1,
            )
            if recent_duplicate:
                return
        else:
            self._append_match_log(BotLogEntry(message=message, level=level))

        self._logger.log(level, "frame=%s %s", game_state.frame, message, **kwargs)

    def _append_match_log(self, entry: BotLogEntry) -> None:
        self._match_logs.append(entry)


def _format_message(msg: object, args: tuple[object, ...]) -> str:
    if args:
        return str(msg) % args
    return str(msg)


def _render_entry(entry: BotLogEntry) -> str:
    repeated = (
        ""
        if entry.repetition_count == 0
        else f" (repeated {entry.repetition_count} additional times)"
    )
    level_name = _LEVEL_NAMES.get(entry.level, f"Level {entry.level}")
    return f"{level_name} | {entry.message}{repeated}\n"


def _truncate_utf8(value: str, byte_limit: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= byte_limit:
        return value
    suffix = " [truncated]"
    prefix_limit = byte_limit - len(suffix.encode("utf-8"))
    return encoded[:prefix_limit].decode("utf-8", errors="ignore") + suffix
