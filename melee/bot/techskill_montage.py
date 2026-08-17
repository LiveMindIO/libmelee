"""Reusable input montages for common competitive Melee techniques."""

from __future__ import annotations

import math
from enum import Enum, auto
from typing import Final

from melee.bot.character_state import CharacterState, CharacterStatus
from melee.bot.input_montage import InputMontage
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
from melee.enums import Action, Button, Character
from melee.gamestate import GameState, PlayerState


class WavedashDirection(Enum):
    """Horizontal direction for a :class:`WavedashMontage`."""

    Left = auto()
    Right = auto()


class _MultishinePhase(Enum):
    FirstShineRequested = auto()
    JumpRequested = auto()
    SecondShineRequested = auto()


class _WavedashPhase(Enum):
    JumpRequested = auto()
    AirDodgeRequested = auto()
    LandingLag = auto()


class _LedgedashPhase(Enum):
    Ledge = auto()
    ReleaseRequested = auto()
    JumpRequested = auto()
    Rising = auto()
    AirDodgeRequested = auto()
    LandingLag = auto()


_SHINE_ACTIONS: Final = frozenset(
    {
        Action.DOWN_B_GROUND_START,
        Action.DOWN_B_GROUND,
        Action.SHINE_TURN,
        Action.DOWN_B_STUN,
    }
)
_GROUND_MOVEMENT_ACTIONS: Final = frozenset(
    {
        Action.STANDING,
        Action.WALK_SLOW,
        Action.WALK_MIDDLE,
        Action.WALK_FAST,
        Action.TURNING,
        Action.TURNING_RUN,
        Action.DASHING,
        Action.RUNNING,
        Action.RUN_DIRECT,
        Action.RUN_BRAKE,
        Action.CROUCH_START,
        Action.CROUCHING,
        Action.CROUCH_END,
        Action.EDGE_TEETERING_START,
        Action.EDGE_TEETERING,
    }
)
_WAVEDASH_START_ACTIONS: Final = _GROUND_MOVEMENT_ACTIONS | {
    Action.SHIELD,
    Action.SHIELD_START,
    Action.SHIELD_RELEASE,
    Action.SHIELD_REFLECT,
}
_AERIAL_JUMP_ACTIONS: Final = frozenset(
    {
        Action.JUMPING_ARIAL_FORWARD,
        Action.JUMPING_ARIAL_BACKWARD,
    }
)
_DEAD_ACTIONS: Final = frozenset(
    {
        Action.DEAD_DOWN,
        Action.DEAD_LEFT,
        Action.DEAD_RIGHT,
        Action.DEAD_UP,
        Action.DEAD_FLY_STAR,
        Action.DEAD_FLY_STAR_ICE,
        Action.DEAD_FLY,
        Action.DEAD_FLY_SPLATTER,
        Action.DEAD_FLY_SPLATTER_FLAT,
        Action.DEAD_FLY_SPLATTER_ICE,
        Action.DEAD_FLY_SPLATTER_FLAT_ICE,
        Action.DEAD_FALL,
    }
)

# DESNOTE(jbarber, 2026-08-17): A frame-perfect wavedash requests its air dodge
# while observing the character's final KNEE_BEND frame, because controller input
# is committed by the next Console.step. Jump-squat duration is character-specific.
# See https://www.ssbwiki.com/Jump#Jump_squat and
# https://github.com/doldecomp/melee/blob/master/src/melee/ft/chara/ftCommon/ftCo_KneeBend.c
_JUMP_SQUAT_FRAMES: Final[dict[Character, int]] = {
    Character.FOX: 3,
    Character.POPO: 3,
    Character.NANA: 3,
    Character.KIRBY: 3,
    Character.PICHU: 3,
    Character.PIKACHU: 3,
    Character.SAMUS: 3,
    Character.SHEIK: 3,
    Character.CPTFALCON: 4,
    Character.DOC: 4,
    Character.LUIGI: 4,
    Character.MARIO: 4,
    Character.MARTH: 4,
    Character.GAMEANDWATCH: 4,
    Character.NESS: 4,
    Character.YLINK: 4,
    Character.DK: 5,
    Character.FALCO: 5,
    Character.JIGGLYPUFF: 5,
    Character.MEWTWO: 5,
    Character.PEACH: 5,
    Character.ROY: 5,
    Character.YOSHI: 5,
    Character.GANONDORF: 6,
    Character.LINK: 6,
    Character.ZELDA: 6,
    Character.BOWSER: 8,
}


def _player(player_state: CharacterState) -> PlayerState | None:
    return player_state.player()


def _is_interrupted(
    player_state: CharacterState,
    player: PlayerState,
    *,
    include_hitlag: bool,
) -> bool:
    status = player_state.get_state()
    return (
        player.action in _DEAD_ACTIONS
        or (include_hitlag and status is CharacterStatus.HitLag)
        or status
        in {
            CharacterStatus.Hitstun,
            CharacterStatus.GrabbedByEnemy,
            CharacterStatus.ShieldBroken,
        }
    )


def _validate_button(button: Button, allowed: frozenset[Button], name: str) -> None:
    if button not in allowed:
        choices = ", ".join(sorted(item.name for item in allowed))
        raise ValueError(f"{name} must be one of: {choices}")


def _validate_wavedash_angle(angle_degrees: float) -> None:
    if not math.isfinite(angle_degrees):
        raise ValueError("angle_degrees must be finite")
    if not 17.1 <= angle_degrees < 90.0:
        raise ValueError("angle_degrees must be at least 17.1 and less than 90")


def _apply_down_input(controls: SimpleControls, button: Button) -> None:
    controls.release_all()
    controls.tilt_stick(StickReferenceAxis.DOWN, 0.0)
    controls.press_button(button)


def _apply_wavedash_input(
    controls: SimpleControls,
    direction: WavedashDirection,
    angle_degrees: float,
    dodge_button: Button,
) -> None:
    controls.release_all()
    if direction is WavedashDirection.Right:
        controls.tilt_stick(StickReferenceAxis.RIGHT, angle_degrees)
    else:
        controls.tilt_stick(StickReferenceAxis.LEFT, -angle_degrees)
    controls.press_button(dodge_button)


class MultishineMontage(InputMontage):
    """Perform one Fox multishine cycle, ending when the second shine begins."""

    def __init__(
        self,
        frame_limit: int = 24,
        cancel_montage: InputMontage | None = None,
        *,
        jump_button: Button = Button.BUTTON_Y,
    ) -> None:
        super().__init__(frame_limit, cancel_montage)
        _validate_button(
            jump_button,
            frozenset({Button.BUTTON_X, Button.BUTTON_Y}),
            "jump_button",
        )
        self._jump_button = jump_button
        self._phase = _MultishinePhase.FirstShineRequested

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        player = _player(player_state)
        return (
            player is not None
            and player.character is Character.FOX
            and player.action is Action.STANDING
            and player.on_ground
            and not player.off_stage
        )

    def should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        player = _player(player_state)
        abort = (
            player is None
            or player.character is not Character.FOX
            or player.off_stage
            or _is_interrupted(
                player_state,
                player,
                include_hitlag=False,
            )
        )
        return abort

    def on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | bool:
        del opponent_state, state
        player = _player(player_state)
        if player is None:
            controls.release_all()
            return False

        if self._phase is _MultishinePhase.FirstShineRequested:
            _apply_down_input(controls, Button.BUTTON_B)
            self._phase = _MultishinePhase.JumpRequested
            return self

        controls.release_all()
        if self._phase is _MultishinePhase.JumpRequested:
            if player.action in _SHINE_ACTIONS:
                can_jump_cancel = (
                    player.action is Action.DOWN_B_GROUND
                    or player.action_frame >= 4
                )
                if can_jump_cancel and player.on_ground:
                    controls.press_button(self._jump_button)
                return self
            if player.action is Action.KNEE_BEND:
                if player.action_frame < _JUMP_SQUAT_FRAMES[Character.FOX]:
                    return self
                if player.action_frame == _JUMP_SQUAT_FRAMES[Character.FOX]:
                    _apply_down_input(controls, Button.BUTTON_B)
                    self._phase = _MultishinePhase.SecondShineRequested
                    return self
            return False

        if player.action in _SHINE_ACTIONS:
            return True
        if player.action is Action.KNEE_BEND:
            return self
        return False


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
        _validate_wavedash_angle(angle_degrees)
        _validate_button(
            jump_button,
            frozenset({Button.BUTTON_X, Button.BUTTON_Y}),
            "jump_button",
        )
        _validate_button(
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
        player = _player(player_state)
        if (
            player is None
            or player.character not in _JUMP_SQUAT_FRAMES
            or not player.on_ground
            or player.off_stage
            or player.jumps_left <= 0
        ):
            return False
        if player.action not in _WAVEDASH_START_ACTIONS and not (
            player.action in _SHINE_ACTIONS and player.action_frame >= 3
        ):
            return False
        self._character = player.character
        return True

    def should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        player = _player(player_state)
        abort = (
            player is None
            or player.character is not self._character
            or player.off_stage
            or _is_interrupted(
                player_state,
                player,
                include_hitlag=True,
            )
        )
        return abort

    def on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | bool:
        del opponent_state, state
        player = _player(player_state)
        if player is None or self._character is None:
            controls.release_all()
            return False

        controls.release_all()
        if self._phase is _WavedashPhase.JumpRequested:
            if player.action is not Action.KNEE_BEND:
                controls.press_button(self._jump_button)
                return self
            jump_squat_frames = _JUMP_SQUAT_FRAMES[self._character]
            if player.action_frame < jump_squat_frames:
                return self
            if player.action_frame > jump_squat_frames:
                return False
            _apply_wavedash_input(
                controls,
                self._direction,
                self._angle_degrees,
                self._dodge_button,
            )
            self._phase = _WavedashPhase.AirDodgeRequested
            return self

        if self._phase is _WavedashPhase.AirDodgeRequested:
            if player.action is Action.LANDING_SPECIAL and player.on_ground:
                self._phase = _WavedashPhase.LandingLag
                return self
            if player.action is Action.AIRDODGE:
                return self
            return False

        if player.action is Action.LANDING_SPECIAL and player.on_ground:
            return self
        return player.on_ground and player.action in _GROUND_MOVEMENT_ACTIONS


class LedgedashMontage(InputMontage):
    """Release ledge, double jump inward, and waveland onto the main stage.

    The montage releases with the C-stick away to avoid fastfall, jumps inward on
    the first falling frame, and waits until the player's world-space ECB bottom
    exceeds ``minimum_ecb_bottom_y`` before air dodging down and inward. The
    default ``0.25`` threshold is a conservative standard-stage heuristic and may
    be overridden for other stage geometry or character-specific routing.
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
        _validate_wavedash_angle(angle_degrees)
        if not math.isfinite(minimum_ecb_bottom_y):
            raise ValueError("minimum_ecb_bottom_y must be finite")
        _validate_button(
            jump_button,
            frozenset({Button.BUTTON_X, Button.BUTTON_Y}),
            "jump_button",
        )
        _validate_button(
            dodge_button,
            frozenset({Button.BUTTON_L, Button.BUTTON_R}),
            "dodge_button",
        )
        self._angle_degrees = angle_degrees
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
        player = _player(player_state)
        if (
            player is None
            or player.jumps_left <= 0
            or player.action not in {
                Action.EDGE_CATCHING,
                Action.EDGE_HANGING,
            }
        ):
            return False
        self._character = player.character
        self._direction = (
            WavedashDirection.Right
            if float(player.position.x) < 0.0
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
        player = _player(player_state)
        abort = (
            player is None
            or player.character is not self._character
            or _is_interrupted(
                player_state,
                player,
                include_hitlag=True,
            )
        )
        return abort

    def on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | bool:
        del opponent_state, state
        player = _player(player_state)
        if player is None or self._direction is None:
            controls.release_all()
            return False

        controls.release_all()
        if self._phase is _LedgedashPhase.Ledge:
            if player.action is Action.EDGE_CATCHING:
                return self
            if player.action is not Action.EDGE_HANGING:
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
            if player.action is Action.EDGE_HANGING:
                self._phase = _LedgedashPhase.Ledge
                return self
            if player.action is not Action.FALLING or player.jumps_left <= 0:
                return False
            self._apply_inward_drift(controls)
            controls.press_button(self._jump_button)
            self._jumps_before_request = player.jumps_left
            self._phase = _LedgedashPhase.JumpRequested
            return self

        if self._phase in {
            _LedgedashPhase.JumpRequested,
            _LedgedashPhase.Rising,
        }:
            jump_confirmed = player.action in _AERIAL_JUMP_ACTIONS or (
                self._jumps_before_request is not None
                and player.jumps_left < self._jumps_before_request
                and player.speed_y_self > 0.0
            )
            if not jump_confirmed:
                return False
            self._phase = _LedgedashPhase.Rising
            ecb_bottom_y = float(player.position.y) + float(player.ecb.bottom.y)
            if ecb_bottom_y <= self._minimum_ecb_bottom_y:
                self._apply_inward_drift(controls)
                return self
            _apply_wavedash_input(
                controls,
                self._direction,
                self._angle_degrees,
                self._dodge_button,
            )
            self._phase = _LedgedashPhase.AirDodgeRequested
            return self

        if self._phase is _LedgedashPhase.AirDodgeRequested:
            if player.action is Action.LANDING_SPECIAL and player.on_ground:
                self._phase = _LedgedashPhase.LandingLag
                return self
            if player.action is Action.AIRDODGE:
                return self
            return False

        if player.action is Action.LANDING_SPECIAL and player.on_ground:
            return self
        return player.on_ground and player.action in _GROUND_MOVEMENT_ACTIONS

    def _apply_inward_drift(self, controls: SimpleControls) -> None:
        if self._direction is WavedashDirection.Right:
            controls.tilt_stick(StickReferenceAxis.RIGHT, 0.0)
        else:
            controls.tilt_stick(StickReferenceAxis.LEFT, 0.0)


__all__ = [
    "LedgedashMontage",
    "MultishineMontage",
    "WavedashDirection",
    "WavedashMontage",
]
