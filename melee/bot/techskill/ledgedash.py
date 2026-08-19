"""Ledge-to-stage waveland input montage."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Final

from melee.bot.character_state import CharacterState
from melee.bot.input_montage import InputMontage
from melee.bot.simple_controls import SimpleControls
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import (
    GROUND_MOVEMENT_ACTIONS,
    WavedashDirection,
    apply_wavedash_input,
    clamp_wavedash_angle,
    is_interrupted,
    player,
    validate_button,
)
from melee.enums import Action, Button, Character
from melee.gamestate import GameState


class _LedgedashPhase(Enum):
    Ledge = auto()
    ReleaseRequested = auto()
    JumpRequested = auto()
    Rising = auto()
    AirDodgeRequested = auto()
    LandingLag = auto()


@dataclass(frozen=True)
class _LedgedashState:
    phase: _LedgedashPhase
    jumps_before_request: int | None = None


_AERIAL_JUMP_ACTIONS: Final = frozenset({Action.JUMPING_ARIAL_FORWARD, Action.JUMPING_ARIAL_BACKWARD})
_RISING_ACTIONS: Final = _AERIAL_JUMP_ACTIONS | {
    Action.FALLING,
    Action.FALLING_FORWARD,
    Action.FALLING_BACKWARD,
    Action.FALLING_AERIAL,
    Action.FALLING_AERIAL_FORWARD,
    Action.FALLING_AERIAL_BACKWARD,
}


class LedgedashMontage(StatefulInputMontage[_LedgedashState]):
    """Release ledge, double jump inward, and waveland onto the main stage.

    The montage releases with the C-stick away to avoid fastfall, requests the
    inward double jump for one input frame, and waits until the player's
    world-space ECB bottom exceeds ``minimum_ecb_bottom_y`` before air dodging
    down and inward. The jump button remains neutral throughout the rise. The
    default ``0.25`` threshold is a conservative standard-stage heuristic and may
    be overridden for other stage geometry or character-specific routing. Callers
    choose the air-dodge angle explicitly; its boundaries use the same inward
    floating-point clamp as ``WavedashMontage``.
    """

    def __init__(
        self,
        frame_limit: int = 48,
        cancel_montage: InputMontage | None = None,
        *,
        angle_degrees: float,
        minimum_ecb_bottom_y: float = 0.25,
        jump_button: Button = Button.BUTTON_Y,
        dodge_button: Button = Button.BUTTON_L,
    ) -> None:
        super().__init__(frame_limit, _LedgedashState(_LedgedashPhase.Ledge), cancel_montage)
        safe_angle_degrees = clamp_wavedash_angle(angle_degrees)
        if not math.isfinite(minimum_ecb_bottom_y):
            raise ValueError("minimum_ecb_bottom_y must be finite")
        validate_button(jump_button, frozenset({Button.BUTTON_X, Button.BUTTON_Y}), "jump_button")
        validate_button(dodge_button, frozenset({Button.BUTTON_L, Button.BUTTON_R}), "dodge_button")
        self._angle_degrees = safe_angle_degrees
        self._minimum_ecb_bottom_y = minimum_ecb_bottom_y
        self._jump_button = jump_button
        self._dodge_button = dodge_button
        self._character: Character | None = None
        self._direction: WavedashDirection | None = None

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        if (
            player_state_value is None
            or player_state_value.jumps_left <= 0
            or player_state_value.action not in {Action.EDGE_CATCHING, Action.EDGE_HANGING}
        ):
            return False
        self._character = player_state_value.character
        self._direction = (
            WavedashDirection.Right if float(player_state_value.position.x) < 0.0 else WavedashDirection.Left
        )
        return True

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _LedgedashState,
    ) -> bool:
        del controls, opponent_state, state, input_state
        player_state_value = player(player_state)
        return (
            player_state_value is None
            or player_state_value.character is not self._character
            or is_interrupted(player_state, player_state_value, include_hitlag=True)
        )

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _LedgedashState,
    ) -> tuple[_LedgedashState, InputMontage | bool]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None or self._direction is None:
            controls.release_all()
            return input_state, False
        if input_state.phase is _LedgedashPhase.Rising and (
            player_state_value.on_ground or player_state_value.action not in _RISING_ACTIONS
        ):
            return input_state, False

        controls.release_all()
        match input_state, player_state_value.action:
            case _LedgedashState(phase=_LedgedashPhase.Ledge), Action.EDGE_CATCHING:
                return input_state, self
            case _LedgedashState(phase=_LedgedashPhase.Ledge), Action.EDGE_HANGING:
                controls.tilt_stick(player_state.backward_axis(), 0.0, stick=Button.BUTTON_C)
                return _LedgedashState(_LedgedashPhase.ReleaseRequested), self
            case _LedgedashState(phase=_LedgedashPhase.Ledge), _:
                return input_state, False
            case _LedgedashState(phase=_LedgedashPhase.ReleaseRequested), Action.EDGE_HANGING:
                return _LedgedashState(_LedgedashPhase.Ledge), self
            case _LedgedashState(phase=_LedgedashPhase.ReleaseRequested), Action.FALLING if (
                player_state_value.jumps_left > 0
            ):
                self._apply_inward_drift(controls, player_state)
                controls.press_button(self._jump_button)
                return _LedgedashState(_LedgedashPhase.JumpRequested, player_state_value.jumps_left), self
            case _LedgedashState(phase=_LedgedashPhase.ReleaseRequested), _:
                return input_state, False
            case _LedgedashState(
                phase=_LedgedashPhase.JumpRequested,
                jumps_before_request=jumps_before_request,
            ), action if action in _AERIAL_JUMP_ACTIONS or (
                jumps_before_request is not None
                and player_state_value.jumps_left < jumps_before_request
                and player_state_value.speed_y_self > 0.0
            ):
                input_state = _LedgedashState(_LedgedashPhase.Rising, jumps_before_request)
            case _LedgedashState(phase=_LedgedashPhase.JumpRequested), _:
                return input_state, False
            case _LedgedashState(phase=_LedgedashPhase.Rising), _:
                pass
            case _LedgedashState(phase=_LedgedashPhase.AirDodgeRequested), Action.LANDING_SPECIAL if (
                player_state_value.on_ground
            ):
                return _LedgedashState(_LedgedashPhase.LandingLag), self
            case _LedgedashState(phase=_LedgedashPhase.AirDodgeRequested), Action.AIRDODGE:
                return input_state, self
            case _LedgedashState(phase=_LedgedashPhase.AirDodgeRequested), _:
                return input_state, False
            case _LedgedashState(phase=_LedgedashPhase.LandingLag), Action.LANDING_SPECIAL if (
                player_state_value.on_ground
            ):
                return input_state, self
            case _LedgedashState(phase=_LedgedashPhase.LandingLag), action:
                return input_state, player_state_value.on_ground and action in GROUND_MOVEMENT_ACTIONS

        ecb_bottom_y = float(player_state_value.position.y) + float(player_state_value.ecb.bottom.y)
        if ecb_bottom_y <= self._minimum_ecb_bottom_y:
            self._apply_inward_drift(controls, player_state)
            return input_state, self

        apply_wavedash_input(controls, self._direction, self._angle_degrees, self._dodge_button)
        return _LedgedashState(_LedgedashPhase.AirDodgeRequested), self

    def _apply_inward_drift(self, controls: SimpleControls, player_state: CharacterState) -> None:
        controls.tilt_stick(player_state.forward_axis(), 0.0)


__all__ = ["LedgedashMontage"]
