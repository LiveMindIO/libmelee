"""Grounded wavedash input montage."""

from __future__ import annotations

from enum import Enum, auto
from typing import Final

from melee.bot.character_state import CharacterState
from melee.bot.input_montage import InputMontage
from melee.bot.simple_controls import SimpleControls
from melee.bot.techskill.common import (
    GROUND_MOVEMENT_ACTIONS,
    JUMP_SQUAT_FRAMES,
    SHINE_ACTIONS,
    WavedashDirection,
    apply_wavedash_input,
    is_interrupted,
    player,
    validate_button,
    validate_wavedash_angle,
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


class WavedashMontage(InputMontage):
    """Jump, air dodge down-diagonally, and finish when grounded actionable.

    The air dodge is requested on the character's final jump-squat frame. The
    default 45-degree angle favors reliability; 17.1 degrees is the researched
    maximum-distance boundary and the shallowest accepted value.
    """

    def __init__(
        self,
        direction: WavedashDirection,
        frame_limit: int = 40,
        cancel_montage: InputMontage | None = None,
        *,
        angle_degrees: float = 45.0,
        jump_button: Button = Button.BUTTON_Y,
        dodge_button: Button = Button.BUTTON_L,
    ) -> None:
        super().__init__(frame_limit, cancel_montage)
        if not isinstance(direction, WavedashDirection):
            raise ValueError("direction must be a WavedashDirection")
        validate_wavedash_angle(angle_degrees)
        validate_button(
            jump_button,
            frozenset({Button.BUTTON_X, Button.BUTTON_Y}),
            "jump_button",
        )
        validate_button(
            dodge_button,
            frozenset({Button.BUTTON_L, Button.BUTTON_R}),
            "dodge_button",
        )
        self._direction = direction
        self._angle_degrees = angle_degrees
        self._jump_button = jump_button
        self._dodge_button = dodge_button
        self._phase = _WavedashPhase.JumpRequested
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
            player_state_value.action in SHINE_ACTIONS
            and player_state_value.action_frame >= 3
        ):
            return False
        self._character = player_state_value.character
        return True

    def should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        return (
            player_state_value is None
            or player_state_value.character is not self._character
            or player_state_value.off_stage
            or is_interrupted(
                player_state,
                player_state_value,
                include_hitlag=True,
            )
        )

    def on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | bool:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None or self._character is None:
            controls.release_all()
            return False

        controls.release_all()
        if self._phase is _WavedashPhase.JumpRequested:
            if player_state_value.action is not Action.KNEE_BEND:
                controls.press_button(self._jump_button)
                return self
            jump_squat_frames = JUMP_SQUAT_FRAMES[self._character]
            if player_state_value.action_frame < jump_squat_frames:
                return self
            if player_state_value.action_frame > jump_squat_frames:
                return False
            apply_wavedash_input(
                controls,
                self._direction,
                self._angle_degrees,
                self._dodge_button,
            )
            self._phase = _WavedashPhase.AirDodgeRequested
            return self

        if self._phase is _WavedashPhase.AirDodgeRequested:
            if (
                player_state_value.action is Action.LANDING_SPECIAL
                and player_state_value.on_ground
            ):
                self._phase = _WavedashPhase.LandingLag
                return self
            if player_state_value.action is Action.AIRDODGE:
                return self
            return False

        if (
            player_state_value.action is Action.LANDING_SPECIAL
            and player_state_value.on_ground
        ):
            return self
        return (
            player_state_value.on_ground
            and player_state_value.action in GROUND_MOVEMENT_ACTIONS
        )


__all__ = ["WavedashDirection", "WavedashMontage"]
