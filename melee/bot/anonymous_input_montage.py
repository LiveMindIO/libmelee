"""Callable-defined stateful controller-input montages."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

from melee.bot.input_montage import InputMontage
from melee.bot.stateful_input_montage import StatefulInputMontage

if TYPE_CHECKING:
    from melee.bot.character_state import CharacterState
    from melee.bot.simple_controls import SimpleControls
    from melee.gamestate import GameState


StateT = TypeVar("StateT")


class AnonymousInputMontage(StatefulInputMontage[StateT]):
    """A stateful montage defined entirely by supplied callables.

    The required ``cancel`` callable receives the latest typed state during
    active cancellation and may return a fallback montage for the caller's next
    game tick. It is not called for waiting or terminal montages.
    """

    def __init__(
        self,
        *,
        frame_limit: int,
        initial_state: StateT,
        can_start: Callable[
            [SimpleControls, CharacterState, CharacterState, GameState],
            bool,
        ],
        on_tick: Callable[
            [SimpleControls, CharacterState, CharacterState, GameState, StateT],
            tuple[StateT, InputMontage | bool],
        ],
        should_abort: Callable[
            [SimpleControls, CharacterState, CharacterState, GameState, StateT],
            bool,
        ],
        cancel: Callable[
            [SimpleControls, CharacterState, CharacterState, GameState, StateT],
            InputMontage | None,
        ],
    ) -> None:
        super().__init__(frame_limit, initial_state)
        self._can_start = can_start
        self._on_tick = on_tick
        self._should_abort = should_abort
        self._cancel = cancel

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        return self._can_start(controls, player_state, opponent_state, state)

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: StateT,
    ) -> tuple[StateT, InputMontage | bool]:
        return self._on_tick(controls, player_state, opponent_state, state, input_state)

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: StateT,
    ) -> bool:
        return self._should_abort(controls, player_state, opponent_state, state, input_state)

    def stateful_cancel(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: StateT,
    ) -> InputMontage | None:
        return self._cancel(controls, player_state, opponent_state, state, input_state)


__all__ = ["AnonymousInputMontage"]
