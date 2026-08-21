"""Protocols for libmelee Python bots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar, runtime_checkable

from melee.bot.character_state import CharacterState
from melee.bot.logger import BotLogger
from melee.bot.match_history import MatchHistory
from melee.bot.simple_controls import SimpleControls
from melee.controller import Controller
from melee.enums import Character
from melee.framedata import FrameData
from melee.gamestate import GameState

A = TypeVar("A", contravariant=True)


@dataclass(frozen=True)
class CharacterSelection:
    """A bot's declarative character-select preference for one match."""

    character: Character
    costume_preference: int | None = None
    name_tag: str | None = None


@runtime_checkable
class Strategy(Protocol[A]):
    """Composable interface for one frame of in-game bot logic."""

    def game_tick(
        self,
        port: int,
        match_number: int,
        game_state: GameState,
        controller: Controller,
        simple_controls: SimpleControls,
        frame_data: FrameData,
        player_state: CharacterState,
        opponent_state: CharacterState,
        custom: A,
        *,
        logger: BotLogger,
    ) -> None:
        """Run one frame of strategy logic with the owning bot's logger."""
        ...


@runtime_checkable
class BotProtocol(Protocol[A]):
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
        player_state: CharacterState,
        opponent_state: CharacterState,
        custom: A,
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
            player_state: Read-only :class:`CharacterState` for this bot's port.
                Use ``player_state.get_state()``, ``player_state.can_attack()``,
                ``player_state.is_grabbing()``, etc. for high-level combat
                classification. Access the raw :class:`melee.gamestate.PlayerState`
                via ``player_state.player()`` when you need per-frame fields like
                ``position`` or ``facing``.
            opponent_state: Read-only :class:`CharacterState` for the nearest
                opposing port this frame.
            custom: Runtime-defined per-frame data. The embedding application
                selects its type and semantics when specializing this protocol.
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


# DESNOTE(jbarber, 2026-08-21): Published bot sources import CrowdControl, so
# retain the old name while new source migrates to BotProtocol.
CrowdControl = BotProtocol
