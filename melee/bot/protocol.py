"""Protocol for Crowd Control Python bots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from melee.controller import Controller
from melee.enums import Character
from melee.framedata import FrameData
from melee.gamestate import GameState, PlayerState

from melee.bot.logger import BotLogger
from melee.bot.match_history import MatchHistory
from melee.bot.simple_controls import SimpleControls


@dataclass(frozen=True)
class CharacterSelection:
    """A bot's declarative character-select preference for one match."""

    character: Character
    costume_preference: int | None = None
    name_tag: str | None = None


@runtime_checkable
class CrowdControl(Protocol):
    """Interface implemented by Python bots controlled through libmelee."""

    def set_logger(self, logger: BotLogger) -> None:
        """Receive the profile-scoped logger constructed by the runtime."""
        ...

    def get_logger(self) -> BotLogger:
        """Return this bot's deduplicating status logger."""
        ...

    def game_tick(
        self,
        port: int,
        match_number: int,
        game_state: GameState,
        controller: Controller,
        simple_controls: SimpleControls,
        frame_data: FrameData,
        player_state: PlayerState | None,
        opponent_state: PlayerState | None,
    ) -> None:
        """Run one frame of in-game AI logic.

        Args:
            port: Controller port (1-4) this bot controls.
            match_number: One-indexed match counter for the current session.
            game_state: Full libmelee game state for this frame.
            controller: Virtual controller receiving this bot's inputs.
            simple_controls: Per-frame :class:`SimpleControls` bound to ``port``.
            frame_data: Shared libmelee ``FrameData`` helper, loaded once and
                reused across every bot and match. Use it for spacing, punish,
                and recovery queries instead of constructing your own.
            player_state: This bot's ``PlayerState`` this frame, or ``None`` when
                absent (equivalent to ``game_state.players.get(port)``).
            opponent_state: The nearest opposing ``PlayerState`` in the match this
                frame, or ``None`` when no opponent is present.
        """

    def select_character(
        self,
        port: int,
        match_number: int,
        match_history: MatchHistory,
    ) -> CharacterSelection:
        """Return the character selection to apply for this match.

        The runtime owns all character-select controller input so every player
        locks in before the centrally selected stage is started.
        """
        ...
