"""Platform drop followed by the earliest native fast-fall input."""

from __future__ import annotations

from enum import Enum, auto

from melee.bot.character_state import CharacterState
from melee.bot.input_montage import Abort, InputMontage
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player
from melee.enums import Action, Character
from melee.gamestate import GameState


class _PlatformDropPhase(Enum):
    Grounded = auto()
    DropRequested = auto()
    NeutralRequested = auto()
    FastFallRequested = auto()


class PlatformDropFastFallMontage(StatefulInputMontage[_PlatformDropPhase]):
    """Drop through a semisolid, reset down input, then confirm fast fall.

    Melee resets its main-stick Y tap timer when entering ``PLATFORM_DROP``.
    Holding the original down input therefore cannot fast fall. This montage
    observes the drop, commits one neutral input frame, presses down again, and
    succeeds only after character-specific fast-fall speed is observed.
    """

    def __init__(
        self,
        frame_limit: int = 24,
        cancel_montage: InputMontage | None = None,
    ) -> None:
        super().__init__(frame_limit, _PlatformDropPhase.Grounded, cancel_montage)
        self._character: Character | None = None

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None or not player_state.can_platform_drop():
            return False
        self._character = player_state_value.character
        return True

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _PlatformDropPhase,
    ) -> Abort | None:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character is not self._character:
            return Abort("player character changed")
        if is_interrupted(player_state, player_state_value, include_hitlag=True):
            return Abort("player was interrupted")
        if input_state in {_PlatformDropPhase.Grounded, _PlatformDropPhase.DropRequested}:
            if player_state_value.on_ground and not player_state.can_platform_drop():
                return Abort("player can no longer drop through the platform")
            if not player_state_value.on_ground and player_state_value.action is not Action.PLATFORM_DROP:
                return Abort("player left the platform without dropping through it")
            return None
        if player_state_value.action not in {Action.PLATFORM_DROP, Action.FALLING}:
            return Abort("player left the platform-drop fall state")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _PlatformDropPhase,
    ) -> tuple[_PlatformDropPhase, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            controls.release_all()
            return input_state, Abort("player state became unavailable")

        controls.release_all()
        if input_state in {_PlatformDropPhase.Grounded, _PlatformDropPhase.DropRequested}:
            if player_state_value.action is Action.PLATFORM_DROP:
                return _PlatformDropPhase.NeutralRequested, self
            if not controls.platform_drop():
                return input_state, Abort("platform drop input became unavailable")
            return _PlatformDropPhase.DropRequested, self
        if input_state is _PlatformDropPhase.NeutralRequested:
            controls.tilt_stick(StickReferenceAxis.DOWN, 0.0)
            return _PlatformDropPhase.FastFallRequested, self
        if self._is_fast_falling(player_state):
            return input_state, True
        controls.tilt_stick(StickReferenceAxis.DOWN, 0.0)
        return input_state, self

    @staticmethod
    def _is_fast_falling(player_state: CharacterState) -> bool:
        player_state_value = player(player_state)
        if player_state_value is None:
            return False
        attributes = player_state.frame_data.characterdata.get(player_state_value.character)
        if attributes is None:
            return False
        fast_fall_speed = float(attributes["FastFallSpeed"])
        return float(player_state_value.speed_y_self) <= -fast_fall_speed


__all__ = ["PlatformDropFastFallMontage"]
