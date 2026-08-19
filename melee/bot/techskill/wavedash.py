"""Grounded wavedash input montage."""

from __future__ import annotations

from enum import Enum, auto
from typing import Final

from melee.bot.character_state import CharacterState
from melee.bot.input_montage import InputMontage
from melee.bot.simple_controls import SimpleControls
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import (
    GROUND_MOVEMENT_ACTIONS,
    JUMP_SQUAT_FRAMES,
    SHINE_ACTIONS,
    WavedashDirection,
    apply_wavedash_input,
    clamp_wavedash_angle,
    is_interrupted,
    player,
    validate_button,
)
from melee.enums import Action, Button, Character
from melee.gamestate import GameState


class _WavedashPhase(Enum):
    JumpRequested = auto()
    AirDodgeRequested = auto()
    LandingLag = auto()


_WAVEDASH_START_ACTIONS: Final = GROUND_MOVEMENT_ACTIONS | {
    Action.SHIELD,
    Action.SHIELD_START,
    Action.SHIELD_RELEASE,
    Action.SHIELD_REFLECT,
}


class WavedashMontage(StatefulInputMontage[_WavedashPhase]):
    """Jump, air dodge down-diagonally, and finish when grounded actionable.

    The air dodge is requested on the character's final jump-squat frame. The
    Callers choose the air-dodge angle explicitly; 17.1 degrees is the shallow
    boundary. Boundary requests and one-ULP roundoff are clamped
    to a representable float strictly inside the accepted interval.
    """

    def __init__(
        self,
        direction: WavedashDirection,
        frame_limit: int = 40,
        cancel_montage: InputMontage | None = None,
        *,
        angle_degrees: float,
        jump_button: Button = Button.BUTTON_Y,
        dodge_button: Button = Button.BUTTON_L,
    ) -> None:
        super().__init__(frame_limit, _WavedashPhase.JumpRequested, cancel_montage)
        if not isinstance(direction, WavedashDirection):
            raise ValueError("direction must be a WavedashDirection")
        safe_angle_degrees = clamp_wavedash_angle(angle_degrees)
        validate_button(jump_button, frozenset({Button.BUTTON_X, Button.BUTTON_Y}), "jump_button")
        validate_button(dodge_button, frozenset({Button.BUTTON_L, Button.BUTTON_R}), "dodge_button")
        self._direction = direction
        self._angle_degrees = safe_angle_degrees
        self._jump_button = jump_button
        self._dodge_button = dodge_button
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
        if (
            player_state_value is None
            or player_state_value.character not in JUMP_SQUAT_FRAMES
            or not player_state_value.on_ground
            or player_state_value.off_stage
            or player_state_value.jumps_left <= 0
        ):
            return False
        if player_state_value.action not in _WAVEDASH_START_ACTIONS and not (
            player_state_value.action in SHINE_ACTIONS and player_state_value.action_frame >= 3
        ):
            return False
        self._character = player_state_value.character
        return True

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _WavedashPhase,
    ) -> bool:
        del controls, opponent_state, state, input_state
        player_state_value = player(player_state)
        return (
            player_state_value is None
            or player_state_value.character is not self._character
            or player_state_value.off_stage
            or is_interrupted(player_state, player_state_value, include_hitlag=True)
        )

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _WavedashPhase,
    ) -> tuple[_WavedashPhase, InputMontage | bool]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None or self._character is None:
            controls.release_all()
            return input_state, False

        controls.release_all()
        match input_state, player_state_value.action:
            case _WavedashPhase.JumpRequested, Action.KNEE_BEND:
                jump_squat_frames = JUMP_SQUAT_FRAMES[self._character]
                if player_state_value.action_frame < jump_squat_frames:
                    return input_state, self
                if player_state_value.action_frame > jump_squat_frames:
                    return input_state, False
                apply_wavedash_input(controls, self._direction, self._angle_degrees, self._dodge_button)
                return _WavedashPhase.AirDodgeRequested, self
            case _WavedashPhase.JumpRequested, action if player_state_value.on_ground and (
                action in _WAVEDASH_START_ACTIONS or (action in SHINE_ACTIONS and player_state_value.action_frame >= 3)
            ):
                controls.press_button(self._jump_button)
                return input_state, self
            case _WavedashPhase.JumpRequested, _:
                return input_state, False
            case _WavedashPhase.AirDodgeRequested, Action.LANDING_SPECIAL if player_state_value.on_ground:
                return _WavedashPhase.LandingLag, self
            case _WavedashPhase.AirDodgeRequested, Action.AIRDODGE:
                return input_state, self
            case _WavedashPhase.AirDodgeRequested, _:
                return input_state, False
            case _WavedashPhase.LandingLag, Action.LANDING_SPECIAL if player_state_value.on_ground:
                return input_state, self
            case _WavedashPhase.LandingLag, action:
                return input_state, player_state_value.on_ground and action in GROUND_MOVEMENT_ACTIONS


__all__ = ["WavedashDirection", "WavedashMontage"]
