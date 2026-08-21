"""Stateful, composable in-game bot strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from melee.bot.character_state import CharacterState
from melee.bot.listener import Listener, ListenerOrCallable, Listeners
from melee.bot.simple_controls import SimpleControls
from melee.controller import Controller
from melee.framedata import FrameData
from melee.gamestate import GameState

A = TypeVar("A")


@dataclass(frozen=True)
class Continue:
    """Signal that the active strategy should receive the next game tick."""


@dataclass(frozen=True)
class Exit:
    """Signal that the active strategy has exited for ``reason``."""

    reason: str


class Strategy(ABC, Generic[A]):
    """Stateful compartment for a bot's in-game frame logic.

    Strategy instances retain implementation-defined state. A bot may instantiate
    the same strategy class multiple times during one match; each instance owns an
    independent lifecycle and should be discarded after returning :class:`Exit`.
    """

    def __init__(self, name: str, description: str) -> None:
        self._name = name
        self._description = description
        self._exit_listeners: Listeners[[Exit], None] = Listeners()

    def get_name(self) -> str:
        """Return this strategy instance's display name."""
        return self._name

    def get_description(self) -> str:
        """Return this strategy instance's description."""
        return self._description

    def add_exit_listener(self, listener: ListenerOrCallable[[Exit], None]) -> Listener[[Exit], None]:
        """Register and return a listener notified when this strategy exits."""
        return self._exit_listeners.add(listener)

    def get_exit_listeners(self) -> Listeners[[Exit], None]:
        """Return this strategy's exit-listener collection."""
        return self._exit_listeners

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
    ) -> Continue | Exit:
        """Run one frame and notify exit listeners when this strategy exits."""
        result = self.tick(
            port,
            match_number,
            game_state,
            controller,
            simple_controls,
            frame_data,
            player_state,
            opponent_state,
            custom,
        )
        if isinstance(result, Exit):
            for listener in self._exit_listeners.get_all():
                listener(result)
        return result

    @abstractmethod
    def tick(
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
    ) -> Continue | Exit:
        """Implement one frame of strategy logic."""


__all__ = ["Continue", "Exit", "Strategy"]
