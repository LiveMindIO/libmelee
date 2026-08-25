"""Short-lived, composable controller-input sequences for bots."""

from __future__ import annotations

import logging
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Self

from melee.bot.listener import ListenerOrCallable, Listeners

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from melee.bot.character_state import CharacterState
    from melee.bot.simple_controls import SimpleControls
    from melee.gamestate import GameState


def _warn_legacy_result(message: str) -> None:
    """Warn when a montage uses a compatibility-only result form."""
    warnings.warn(message, DeprecationWarning, stacklevel=3)


@dataclass(frozen=True)
class Abort:
    """Signal that an input montage aborted for ``reason``."""

    reason: str


class MontageState(Enum):
    """Lifecycle state of a single-use :class:`InputMontage` instance."""

    Waiting = auto()
    Active = auto()
    TimedOut = auto()
    Cancelled = auto()
    Aborted = auto()
    Finished = auto()


class PreTickResult(Enum):
    """Pre-tick control flow with abort-over-completion-over-continue precedence."""

    CONTINUE = auto()
    """Run the montage's normal input tick."""

    EARLY_COMPLETION = auto()
    """Skip the input tick and continue through successful branch selection."""

    ABORTED = auto()
    """Legacy reasonless abort retained for compatibility."""

    @staticmethod
    def Aborted(reason: str) -> Abort:
        """Create an abort result carrying ``reason``."""
        return Abort(reason)

    def combine(self, other: PreTickResult) -> PreTickResult:
        """Return the higher-precedence result from two listeners."""
        match self, other:
            case (PreTickResult.ABORTED, _) | (_, PreTickResult.ABORTED):
                return PreTickResult.ABORTED
            case (PreTickResult.EARLY_COMPLETION, _) | (_, PreTickResult.EARLY_COMPLETION):
                return PreTickResult.EARLY_COMPLETION
            case PreTickResult.CONTINUE, PreTickResult.CONTINUE:
                return PreTickResult.CONTINUE


class InputMontage(ABC):
    """A short-lived input sequence advanced once per bot tick.

    A montage instance is single-use. Call :meth:`tick` once per game tick and
    retain the returned montage while the sequence is in progress. A montage may
    return itself, or return a different montage to hand control to a follow-up
    or branch. ``True`` means the sequence completed successfully and
    :class:`Abort` carries a terminal failure reason.

    Use :meth:`add_branch` to choose a follow-up from the current game state.
    A successful montage becomes finished, then returns the first eligible
    branch for the caller to advance on the next game tick. If no configured
    branch can start, the montage aborts.

    Call :meth:`cancel` rather than dropping an active montage when its sequence
    is no longer wanted. Cancellation neutralizes pending controller input,
    changes the lifecycle state to :attr:`MontageState.Cancelled`, and returns
    the optional ``cancel_montage`` fallback for the caller to retain and advance
    on the next game tick. Waiting and terminal montages cannot be cancelled.

    ``frame_limit`` counts calls to :meth:`on_tick`, not time spent waiting for
    :meth:`can_start`. The limit is a safety boundary; implementations should
    return :class:`Abort` as soon as their own success conditions become
    impossible. Every transition to :attr:`MontageState.Aborted` returns that
    value and logs the montage name and reason at WARNING.
    """

    def __init__(
        self,
        frame_limit: int,
        cancel_montage: InputMontage | None = None,
        *,
        name: str | None = None,
    ) -> None:
        if frame_limit <= 0:
            raise ValueError("frame_limit must be greater than zero")

        self._frame_limit = frame_limit
        self._frame_count = 0
        self._cancel_montage = cancel_montage
        self._name = type(self).__name__ if name is None else name
        self._montage_state = MontageState.Waiting
        self._branches: list[InputMontage] = []
        self._abort_listeners: Listeners[[Abort], None] = Listeners()
        self._pre_tick_listeners: Listeners[
            [SimpleControls, CharacterState, CharacterState, GameState],
            PreTickResult | Abort,
        ] = Listeners()

    def get_name(self) -> str:
        """Return this montage instance's configured name."""
        return self._name

    def add_branch(self, montage: InputMontage) -> Self:
        """Append a possible follow-up montage and return this montage.

        Branches are considered in insertion order after this montage's own
        segment succeeds. The first waiting branch whose :meth:`can_start`
        returns ``True`` becomes the active continuation.
        """
        if montage is self:
            raise ValueError("a montage cannot branch to itself")
        self._branches.append(montage)
        return self

    def add_abort_listener(
        self,
        listener: ListenerOrCallable[[Abort], None],
    ) -> Self:
        """Append a listener notified when this montage aborts."""
        self._abort_listeners.add(listener)
        return self

    def get_abort_listeners(self) -> Listeners[[Abort], None]:
        """Return the abort-listener collection."""
        return self._abort_listeners

    def add_pre_tick_listener(
        self,
        listener: ListenerOrCallable[
            [SimpleControls, CharacterState, CharacterState, GameState],
            PreTickResult | Abort,
        ],
    ) -> Self:
        """Append a listener that may continue, complete, or abort before the input tick."""
        self._pre_tick_listeners.add(listener)
        return self

    def get_pre_tick_listeners(
        self,
    ) -> Listeners[
        [SimpleControls, CharacterState, CharacterState, GameState],
        PreTickResult | Abort,
    ]:
        """Return the pre-tick listener collection."""
        return self._pre_tick_listeners

    def get_montage_state(self) -> MontageState:
        """Return this montage's current lifecycle state."""
        return self._montage_state

    def tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | bool | Abort:
        """Advance this montage by at most one active input frame.

        Waiting and active montages return a montage for the caller to retain.
        A montage that succeeds may return an eligible branch for the next call.
        Terminal montages always return ``False`` on later calls and cannot be
        restarted.
        """
        if self._montage_state not in {MontageState.Waiting, MontageState.Active}:
            return False

        if self._montage_state is MontageState.Waiting:
            if not self.can_start(controls, player_state, opponent_state, state):
                return self
            self._montage_state = MontageState.Active

        if self._frame_count >= self._frame_limit:
            controls.release_all()
            self._montage_state = MontageState.TimedOut
            return False

        should_abort = self.should_abort(controls, player_state, opponent_state, state)
        if isinstance(should_abort, Abort):
            return self._abort(controls, should_abort)
        if isinstance(should_abort, bool):
            _warn_legacy_result(
                "Returning bool from InputMontage.should_abort() is deprecated; return Abort(reason) or None instead."
            )
        if should_abort:
            return self._abort(controls, Abort("should_abort returned True"))

        pre_tick_result = PreTickResult.CONTINUE
        pre_tick_abort: Abort | None = None
        for listener in self._pre_tick_listeners.get_all():
            listener_result = listener(controls, player_state, opponent_state, state)
            if isinstance(listener_result, Abort):
                if pre_tick_abort is None:
                    pre_tick_abort = listener_result
            else:
                if listener_result is PreTickResult.ABORTED:
                    _warn_legacy_result(
                        "PreTickResult.ABORTED is deprecated; return PreTickResult.Aborted(reason) instead."
                    )
                pre_tick_result = pre_tick_result.combine(listener_result)

        if pre_tick_abort is not None:
            return self._abort(controls, pre_tick_abort)
        if pre_tick_result is PreTickResult.ABORTED:
            return self._abort(controls, Abort("pre-tick listener returned ABORTED"))
        if pre_tick_result is PreTickResult.EARLY_COMPLETION:
            return self._continue_to_branch_or_finish(controls, player_state, opponent_state, state)

        result = self.on_tick(controls, player_state, opponent_state, state)
        self._frame_count += 1

        match result:
            case Abort() as abort:
                return self._abort(controls, abort)
            case True:
                return self._continue_to_branch_or_finish(controls, player_state, opponent_state, state)
            case False:
                _warn_legacy_result(
                    "Returning False from InputMontage.on_tick() is deprecated; return Abort(reason) instead."
                )
                return self._abort(controls, Abort("on_tick returned False"))
            case InputMontage() as next_montage if next_montage is not self:
                self._montage_state = MontageState.Finished
                return next_montage
            case InputMontage() as next_montage:
                return next_montage
            case _:
                self._abort(
                    controls,
                    Abort(f"on_tick returned unsupported type {type(result).__name__}"),
                )
                raise TypeError("on_tick must return an InputMontage, Abort, or bool")

    def _continue_to_branch_or_finish(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | bool | Abort:
        self._montage_state = MontageState.Finished
        if not self._branches:
            return True

        for branch in self._branches:
            if branch._montage_state is not MontageState.Waiting:
                continue
            if not branch.can_start(controls, player_state, opponent_state, state):
                continue

            branch._montage_state = MontageState.Active
            return branch

        return self._abort(controls, Abort("no configured branch could start"))

    def _abort(self, controls: SimpleControls, abort: Abort) -> Abort:
        """Neutralize input, enter the aborted state, and return ``abort``."""
        controls.release_all()
        self._montage_state = MontageState.Aborted
        LOGGER.warning("Input montage %s aborted: %s", self._name, abort.reason)
        for listener in self._abort_listeners.get_all():
            listener(abort)
        return abort

    def cancel(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | None:
        """Cancel an active montage and return its configured fallback.

        When active, this neutralizes pending input and changes the lifecycle
        state to :attr:`MontageState.Cancelled`. The returned fallback is a
        next-tick handoff; this method does not advance it. If this montage is
        waiting or terminal, return ``None`` without changing its state or
        controller input.

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
    ) -> InputMontage | bool | Abort:
        """Apply one active frame and report what should happen next.

        Return ``self`` to continue this montage on the next game tick, another
        montage to hand off control, ``True`` on success, or :class:`Abort` on
        failure. ``False`` remains accepted as a deprecated compatibility abort
        without a custom reason.
        """
        raise NotImplementedError

    @abstractmethod
    def should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> Abort | bool | None:
        """Return an abort reason when game state invalidates the sequence.

        Examples include an aerial-attack montage whose character is no longer
        airborne, a jump montage when no jump is available, or any sequence that
        was interrupted because the character was hit. Boolean results remain
        accepted as deprecated compatibility values; return ``None`` to continue.
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


__all__ = ["Abort", "InputMontage", "MontageState", "PreTickResult"]
