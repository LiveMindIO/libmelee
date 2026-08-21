"""Stateful base class for composable libmelee bots."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from melee.bot.character_state import CharacterState
from melee.bot.input_montage import InputMontage
from melee.bot.listener import Listener, ListenerOrCallable, Listeners
from melee.bot.logger import BotLogger
from melee.bot.match_history import MatchHistory
from melee.bot.protocol import BotProtocol, CharacterSelection
from melee.bot.simple_controls import SimpleControls
from melee.bot.strategy import Strategy
from melee.controller import Controller
from melee.framedata import FrameData
from melee.gamestate import GameState

A = TypeVar("A")


class BaseBot(BotProtocol[A], ABC, Generic[A]):
    """Base implementation for logger, strategy, and montage state.

    Construction starts with no active strategy or montage. Subclasses that need
    an initial strategy must call ``super().__init__()`` first and then pass the
    strategy to :meth:`set_active_strategy`. That setter immediately mirrors the
    strategy's current montage and propagates later strategy montage changes.
    Assigning ``_active_strategy`` directly bypasses this synchronization.

    Change listeners run in subscription order after the active value is updated.
    Each listener receives ``(previous, current)``. Assigning the same object by
    identity is a no-op.
    """

    def __init__(self) -> None:
        """Initialize empty bot state and install strategy-montage propagation."""
        self._bot_logger: BotLogger | None = None
        self._active_strategy: Strategy[A] | None = None
        self._active_montage: InputMontage | None = None
        self._strategy_montage_listener_identifier: str | None = None
        self._strategy_changed_listeners: Listeners[[Strategy[A] | None, Strategy[A] | None], None] = Listeners()
        self._montage_changed_listeners: Listeners[[InputMontage | None, InputMontage | None], None] = Listeners()
        self.add_strategy_changed_listener(self._on_strategy_changed)

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

    def add_strategy_changed_listener(
        self,
        listener: ListenerOrCallable[[Strategy[A] | None, Strategy[A] | None], None],
    ) -> Listener[[Strategy[A] | None, Strategy[A] | None], None]:
        """Register and return a strategy-change listener."""
        return self._strategy_changed_listeners.add(listener)

    def get_strategy_changed_listeners(
        self,
    ) -> Listeners[[Strategy[A] | None, Strategy[A] | None], None]:
        """Return the strategy-change listener collection."""
        return self._strategy_changed_listeners

    def set_active_strategy(self, strategy: Strategy[A] | None) -> None:
        """Set the strategy, synchronize its montage, and notify listeners.

        The previous strategy's montage listener is removed before the new
        strategy is observed. The new strategy's current montage is copied to
        this bot before later strategy-change listeners run. Passing ``None``
        clears the bot's active montage. Use this method instead of assigning
        ``_active_strategy`` directly.
        """
        previous = self._active_strategy
        if previous is strategy:
            return
        self._active_strategy = strategy
        for listener in self._strategy_changed_listeners.get_all():
            listener(previous, strategy)

    def _on_strategy_changed(
        self,
        previous: Strategy[A] | None,
        current: Strategy[A] | None,
    ) -> None:
        if previous is not None and self._strategy_montage_listener_identifier is not None:
            previous.get_montage_changed_listeners().remove(self._strategy_montage_listener_identifier)
        self._strategy_montage_listener_identifier = None

        if current is None:
            self.set_active_montage(None)
            return

        listener = current.add_montage_changed_listener(self._on_strategy_montage_changed)
        self._strategy_montage_listener_identifier = listener.identifier
        self.set_active_montage(current.get_active_montage())

    def _on_strategy_montage_changed(
        self,
        _previous: InputMontage | None,
        current: InputMontage | None,
    ) -> None:
        self.set_active_montage(current)

    def get_active_montage(self) -> InputMontage | None:
        """Return the input montage currently owned by this bot, if any."""
        return self._active_montage

    def add_montage_changed_listener(
        self,
        listener: ListenerOrCallable[[InputMontage | None, InputMontage | None], None],
    ) -> Listener[[InputMontage | None, InputMontage | None], None]:
        """Register and return a montage-change listener."""
        return self._montage_changed_listeners.add(listener)

    def get_montage_changed_listeners(
        self,
    ) -> Listeners[[InputMontage | None, InputMontage | None], None]:
        """Return the montage-change listener collection."""
        return self._montage_changed_listeners

    def set_active_montage(self, montage: InputMontage | None) -> None:
        """Set the active montage and notify listeners after an identity change."""
        previous = self._active_montage
        if previous is montage:
            return
        self._active_montage = montage
        for listener in self._montage_changed_listeners.get_all():
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
