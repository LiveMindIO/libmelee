"""Typed state adapter for controller-input montages."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, Self, TypeVar

from melee.bot.input_montage import InputMontage, MontageState, PreTickResult
from melee.bot.listener import Listener

if TYPE_CHECKING:
    from melee.bot.character_state import CharacterState
    from melee.bot.simple_controls import SimpleControls
    from melee.gamestate import GameState


StateT = TypeVar("StateT")


class StatefulInputMontage(InputMontage, Generic[StateT]):
    """An input montage whose frame logic explicitly transforms typed state.

    Active cancellation first applies :meth:`InputMontage.cancel`, then calls
    :meth:`stateful_cancel` with the latest typed state. A non-``None`` result
    from that hook overrides the fixed ``cancel_montage`` fallback. Waiting and
    terminal montages do not invoke the hook.
    """

    def __init__(self, frame_limit: int, initial_state: StateT, cancel_montage: InputMontage | None = None) -> None:
        super().__init__(frame_limit, cancel_montage)
        self._input_state = initial_state

    def add_stateful_pre_tick_listener(
        self,
        listener: Listener[
            [
                SimpleControls,
                CharacterState,
                CharacterState,
                GameState,
                StateT,
            ],
            PreTickResult,
        ]
        | Callable[
            [SimpleControls, CharacterState, CharacterState, GameState, StateT],
            PreTickResult,
        ],
    ) -> Self:
        """Append a pre-tick listener that also receives the current typed state."""

        def adapted_listener(
            controls: SimpleControls,
            player_state: CharacterState,
            opponent_state: CharacterState,
            state: GameState,
        ) -> PreTickResult:
            return listener(controls, player_state, opponent_state, state, self._input_state)

        super().add_pre_tick_listener(
            Listener.create(adapted_listener, listener.identifier)
            if isinstance(listener, Listener)
            else adapted_listener
        )
        return self

    def on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | bool:
        self._input_state, result = self.stateful_on_tick(
            controls,
            player_state,
            opponent_state,
            state,
            self._input_state,
        )
        return result

    def should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        return self.stateful_should_abort(controls, player_state, opponent_state, state, self._input_state)

    def cancel(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | None:
        """Cancel this active montage and select a state-aware fallback."""
        if self.get_montage_state() is not MontageState.Active:
            return None

        fallback = super().cancel(controls, player_state, opponent_state, state)
        stateful_fallback = self.stateful_cancel(controls, player_state, opponent_state, state, self._input_state)
        return fallback if stateful_fallback is None else stateful_fallback

    @abstractmethod
    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: StateT,
    ) -> tuple[StateT, InputMontage | bool]:
        """Apply one frame and return the next state followed by the result."""
        raise NotImplementedError

    @abstractmethod
    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: StateT,
    ) -> bool:
        """Return whether this montage should abort from the current state."""
        raise NotImplementedError

    def stateful_cancel(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: StateT,
    ) -> InputMontage | None:
        """Return an optional fallback selected from the latest typed state.

        This hook runs only during active cancellation, after pending input has
        been neutralized and the montage has entered ``Cancelled``. Returning
        ``None`` preserves the constructor's ``cancel_montage`` fallback.
        """
        return None


__all__ = ["StatefulInputMontage"]
