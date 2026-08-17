"""Short-lived, composable controller-input sequences for bots."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from melee.bot.character_state import CharacterState
    from melee.bot.simple_controls import SimpleControls
    from melee.gamestate import GameState


class MontageState(Enum):
    """Lifecycle state of a single-use :class:`InputMontage` instance."""

    Waiting = auto()
    Active = auto()
    TimedOut = auto()
    Cancelled = auto()
    Aborted = auto()
    Finished = auto()


class InputMontage(ABC):
    """A short-lived input sequence advanced once per bot tick.

    A montage instance is single-use. Call :meth:`tick` once per game tick and
    retain the returned montage while the sequence is in progress. A montage may
    return itself, or return a different montage to hand control to a follow-up
    or branch. ``True`` means the sequence completed successfully and ``False``
    means it reached a terminal unsuccessful state.

    ``frame_limit`` counts calls to :meth:`on_tick`, not time spent waiting for
    :meth:`can_start`. The limit is a safety boundary; implementations should
    return ``False`` as soon as their own success conditions become impossible.
    """

    def __init__(
        self,
        frame_limit: int,
        cancel_montage: InputMontage | None = None,
    ) -> None:
        if frame_limit <= 0:
            raise ValueError("frame_limit must be greater than zero")

        self._frame_limit = frame_limit
        self._frame_count = 0
        self._cancel_montage = cancel_montage
        self._montage_state = MontageState.Waiting

    def get_montage_state(self) -> MontageState:
        """Return this montage's current lifecycle state."""
        return self._montage_state

    def tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | bool:
        """Advance this montage by at most one active input frame.

        Waiting and active montages return a montage for the caller to retain.
        Terminal montages always return ``False`` on later calls and cannot be
        restarted.
        """
        if self._montage_state not in {
            MontageState.Waiting,
            MontageState.Active,
        }:
            return False

        if self._montage_state is MontageState.Waiting:
            if not self.can_start(
                controls,
                player_state,
                opponent_state,
                state,
            ):
                return self
            self._montage_state = MontageState.Active

        if self._frame_count >= self._frame_limit:
            controls.release_all()
            self._montage_state = MontageState.TimedOut
            return False

        if self.should_abort(
            controls,
            player_state,
            opponent_state,
            state,
        ):
            controls.release_all()
            self._montage_state = MontageState.Aborted
            return False

        result = self.on_tick(
            controls,
            player_state,
            opponent_state,
            state,
        )
        self._frame_count += 1

        if result is True:
            self._montage_state = MontageState.Finished
            return True
        if result is False:
            controls.release_all()
            self._montage_state = MontageState.Aborted
            return False
        if not isinstance(result, InputMontage):
            controls.release_all()
            self._montage_state = MontageState.Aborted
            raise TypeError("on_tick must return an InputMontage or bool")
        if result is not self:
            self._montage_state = MontageState.Finished
        return result

    def cancel(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | None:
        """Cancel an active montage and return its configured fallback.

        The frame arguments let specialized implementations override this method
        and select a state-dependent cancellation sequence. The base method
        neutralizes pending controller input before returning the fallback.
        """
        del player_state, opponent_state, state
        if self._montage_state is not MontageState.Active:
            return None

        controls.release_all()
        self._montage_state = MontageState.Cancelled
        return self._cancel_montage

    @abstractmethod
    def on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | bool:
        """Apply one active frame and report what should happen next.

        Return ``self`` to continue this montage on the next game tick, another
        montage to hand off control, ``True`` on success, or ``False`` on failure.
        """
        raise NotImplementedError

    @abstractmethod
    def should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        """Return whether game state made continuing the sequence invalid.

        Examples include an aerial-attack montage whose character is no longer
        airborne, a jump montage when no jump is available, or any sequence that
        was interrupted because the character was hit.
        """
        raise NotImplementedError

    @abstractmethod
    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        """Return whether this waiting montage can become active this tick."""
        raise NotImplementedError


__all__ = ["InputMontage", "MontageState"]
