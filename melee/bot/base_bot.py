"""Stateful base class for composable libmelee bots."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Generic, TypeVar

from melee.bot.character_state import CharacterState
from melee.bot.input_montage import InputMontage
from melee.bot.logger import BotLogger
from melee.bot.match_history import MatchHistory
from melee.bot.protocol import CharacterSelection, Strategy
from melee.bot.simple_controls import SimpleControls
from melee.controller import Controller
from melee.framedata import FrameData
from melee.gamestate import GameState

A = TypeVar("A")


class BaseBot(ABC, Generic[A]):
    """Base implementation for logger, strategy, and montage state.

    Change listeners run in subscription order after the active value is updated.
    Each listener receives ``(previous, current)``. Assigning the same object by
    identity is a no-op.
    """

    def __init__(self) -> None:
        self._bot_logger: BotLogger | None = None
        self._active_strategy: Strategy[A] | None = None
        self._active_montage: InputMontage | None = None
        self.on_strategy_changed: list[Callable[[Strategy[A] | None, Strategy[A] | None], None]] = []
        self.on_montage_changed: list[Callable[[InputMontage | None, InputMontage | None], None]] = []

    def set_logger(self, logger: BotLogger) -> None:
        """Store the profile-scoped logger supplied by the runtime."""
        self._bot_logger = logger

    def get_logger(self) -> BotLogger:
        """Return the configured bot logger."""
        if self._bot_logger is None:
            msg = "bot logger has not been configured"
            raise RuntimeError(msg)
        return self._bot_logger

    def get_active_strategy(self) -> Strategy[A] | None:
        """Return the strategy currently owned by this bot, if any."""
        return self._active_strategy

    def set_active_strategy(self, strategy: Strategy[A] | None) -> None:
        """Set the active strategy and notify listeners after an identity change."""
        previous = self._active_strategy
        if previous is strategy:
            return
        self._active_strategy = strategy
        for listener in tuple(self.on_strategy_changed):
            listener(previous, strategy)

    def get_active_montage(self) -> InputMontage | None:
        """Return the input montage currently owned by this bot, if any."""
        return self._active_montage

    def set_active_montage(self, montage: InputMontage | None) -> None:
        """Set the active montage and notify listeners after an identity change."""
        previous = self._active_montage
        if previous is montage:
            return
        self._active_montage = montage
        for listener in tuple(self.on_montage_changed):
            listener(previous, montage)

    @abstractmethod
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
        """Run one frame of in-game AI logic."""

    @abstractmethod
    def select_character(
        self,
        port: int,
        match_number: int,
        match_history: MatchHistory,
    ) -> CharacterSelection:
        """Return the character selection to apply for this match."""
