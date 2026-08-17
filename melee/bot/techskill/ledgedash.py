"""Ledge-to-stage waveland input montage."""

from __future__ import annotations

import math
from enum import Enum, auto
from typing import Final

from melee.bot.character_state import CharacterState
from melee.bot.input_montage import InputMontage
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
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


_AERIAL_JUMP_ACTIONS: Final = frozenset(
    {
        Action.JUMPING_ARIAL_FORWARD,
        Action.JUMPING_ARIAL_BACKWARD,
    }
)


class LedgedashMontage(InputMontage):
    """Release ledge, double jump inward, and waveland onto the main stage.

    The montage releases with the C-stick away to avoid fastfall, jumps inward on
    the first falling frame, and waits until the player's world-space ECB bottom
    exceeds ``minimum_ecb_bottom_y`` before air dodging down and inward. The
    default ``0.25`` threshold is a conservative standard-stage heuristic and may
    be overridden for other stage geometry or character-specific routing. Angle
    boundaries use the same inward floating-point clamp as ``WavedashMontage``.
    """

    def __init__(
        self,
        frame_limit: int = 48,
        cancel_montage: InputMontage | None = None,
        *,
        angle_degrees: float = 45.0,
        minimum_ecb_bottom_y: float = 0.25,
        jump_button: Button = Button.BUTTON_Y,
        dodge_button: Button = Button.BUTTON_L,
    ) -> None:
        super().__init__(frame_limit, cancel_montage)
        safe_angle_degrees = clamp_wavedash_angle(angle_degrees)
        if not math.isfinite(minimum_ecb_bottom_y):
            raise ValueError("minimum_ecb_bottom_y must be finite")
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
        self._angle_degrees = safe_angle_degrees
        self._minimum_ecb_bottom_y = minimum_ecb_bottom_y
        self._jump_button = jump_button
        self._dodge_button = dodge_button
        self._phase = _LedgedashPhase.Ledge
        self._character: Character | None = None
        self._direction: WavedashDirection | None = None
        self._jumps_before_request: int | None = None

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
            or player_state_value.action not in {
                Action.EDGE_CATCHING,
                Action.EDGE_HANGING,
            }
        ):
            return False
        self._character = player_state_value.character
        self._direction = (
            WavedashDirection.Right
            if float(player_state_value.position.x) < 0.0
            else WavedashDirection.Left
        )
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
        if player_state_value is None or self._direction is None:
            controls.release_all()
            return False

        controls.release_all()
        if self._phase is _LedgedashPhase.Ledge:
            if player_state_value.action is Action.EDGE_CATCHING:
                return self
            if player_state_value.action is not Action.EDGE_HANGING:
                return False
            away = (
                StickReferenceAxis.LEFT
                if self._direction is WavedashDirection.Right
                else StickReferenceAxis.RIGHT
            )
            controls.tilt_stick(away, 0.0, stick=Button.BUTTON_C)
            self._phase = _LedgedashPhase.ReleaseRequested
            return self

        if self._phase is _LedgedashPhase.ReleaseRequested:
            if player_state_value.action is Action.EDGE_HANGING:
                self._phase = _LedgedashPhase.Ledge
                return self
            if (
                player_state_value.action is not Action.FALLING
                or player_state_value.jumps_left <= 0
            ):
                return False
            self._apply_inward_drift(controls)
            controls.press_button(self._jump_button)
            self._jumps_before_request = player_state_value.jumps_left
            self._phase = _LedgedashPhase.JumpRequested
            return self

        if self._phase in {
            _LedgedashPhase.JumpRequested,
            _LedgedashPhase.Rising,
        }:
            jump_confirmed = player_state_value.action in _AERIAL_JUMP_ACTIONS or (
                self._jumps_before_request is not None
                and player_state_value.jumps_left < self._jumps_before_request
                and player_state_value.speed_y_self > 0.0
            )
            if not jump_confirmed:
                return False
            self._phase = _LedgedashPhase.Rising
            ecb_bottom_y = float(player_state_value.position.y) + float(
                player_state_value.ecb.bottom.y
            )
            if ecb_bottom_y <= self._minimum_ecb_bottom_y:
                self._apply_inward_drift(controls)
                return self
            apply_wavedash_input(
                controls,
                self._direction,
                self._angle_degrees,
                self._dodge_button,
            )
            self._phase = _LedgedashPhase.AirDodgeRequested
            return self

        if self._phase is _LedgedashPhase.AirDodgeRequested:
            if (
                player_state_value.action is Action.LANDING_SPECIAL
                and player_state_value.on_ground
            ):
                self._phase = _LedgedashPhase.LandingLag
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

    def _apply_inward_drift(self, controls: SimpleControls) -> None:
        if self._direction is WavedashDirection.Right:
            controls.tilt_stick(StickReferenceAxis.RIGHT, 0.0)
        else:
            controls.tilt_stick(StickReferenceAxis.LEFT, 0.0)


__all__ = ["LedgedashMontage"]
