"""Cancelable charged smash-attack input montage."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from melee.bot.character_state import AttackType, CharacterState
from melee.bot.input_montage import Abort, InputMontage
from melee.bot.simple_controls import (
    AttackFrameData,
    Hold,
    SimpleControls,
    StickReferenceAxis,
)
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player
from melee.enums import Button
from melee.gamestate import GameState


_ATTACK_BY_AXIS: Final[dict[StickReferenceAxis, AttackType]] = {
    StickReferenceAxis.UP: AttackType.USMASH,
    StickReferenceAxis.DOWN: AttackType.DSMASH,
    StickReferenceAxis.LEFT: AttackType.LSMASH,
    StickReferenceAxis.RIGHT: AttackType.RSMASH,
}
# The first active tick commits A+stick before Melee's 60-frame maximum charge.
_DEFAULT_FRAME_LIMIT: Final = 61


@dataclass(frozen=True)
class _SmashAttackState:
    hold: Hold | None = None
    frame_data: AttackFrameData | None = None


class _ReleaseInputsMontage(InputMontage):
    def __init__(self) -> None:
        super().__init__(frame_limit=1)

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, player_state, opponent_state, state
        return True

    def should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> Abort | None:
        del controls, player_state, opponent_state, state
        return None

    def on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | bool | Abort:
        del player_state, opponent_state, state
        controls.release_all()
        return True


class SmashAttackMontage(StatefulInputMontage[_SmashAttackState]):
    """Charge one absolute-direction smash until the caller cancels it.

    ``axis`` maps up, down, left, and right to ``USMASH``, ``DSMASH``,
    ``LSMASH``, and ``RSMASH`` respectively. Retain and tick this montage while
    charging, then call :meth:`InputMontage.cancel` on a later game frame to
    release the attack and receive a one-tick release-input fallback. Melee
    automatically releases a fully charged smash; the default
    frame limit covers the initial input plus its 60-frame maximum charge.
    """

    def __init__(
        self,
        axis: StickReferenceAxis,
        frame_limit: int = _DEFAULT_FRAME_LIMIT,
    ) -> None:
        if axis not in _ATTACK_BY_AXIS:
            raise ValueError("axis must be a StickReferenceAxis")
        super().__init__(frame_limit, _SmashAttackState(), _ReleaseInputsMontage())
        self._axis = axis
        self._attack_type = _ATTACK_BY_AXIS[axis]

    def get_framedata(self) -> AttackFrameData | None:
        """Return framedata for the requested smash after charging starts."""
        return self._input_state.frame_data

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        return player_state.can_attack(self._attack_type)

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _SmashAttackState,
    ) -> Abort | None:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if input_state.hold is not None and player_state_value.character is not input_state.hold.character:
            return Abort("player character changed")
        if player_state_value.off_stage:
            return Abort("player moved offstage")
        if is_interrupted(player_state, player_state_value, include_hitlag=True):
            return Abort("player was interrupted")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _SmashAttackState,
    ) -> tuple[_SmashAttackState, InputMontage | bool | Abort]:
        del player_state, opponent_state, state
        result = controls.attack(self._attack_type, hold=input_state.hold)
        if isinstance(result, Hold):
            frame_data = AttackFrameData(
                character=result.character,
                action=result.action,
                frame_data=result.frame_data,
            )
            return replace(input_state, hold=result, frame_data=frame_data), self
        if isinstance(result, AttackFrameData):
            controls.release_all()
            controls.tilt_stick(self._axis, 0.0)
            controls.press_button(Button.BUTTON_A)
            return replace(input_state, frame_data=result), self
        return input_state, Abort("smash attack could not start or continue")


__all__ = ["SmashAttackMontage"]
