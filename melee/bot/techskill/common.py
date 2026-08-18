"""Shared state, validation, and input helpers for techskill montages."""

import math
from enum import Enum, auto
from typing import Final

from melee.bot.character_state import CharacterState, CharacterStatus
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
from melee.enums import Action, Button, Character
from melee.gamestate import PlayerState


class WavedashDirection(Enum):
    """Horizontal wavedash or waveland direction."""

    Left = auto()
    Right = auto()


SHINE_ACTIONS: Final = frozenset(
    {
        Action.DOWN_B_GROUND_START,
        Action.DOWN_B_GROUND,
        Action.SHINE_TURN,
        Action.DOWN_B_STUN,
    }
)
GROUND_MOVEMENT_ACTIONS: Final = frozenset(
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

DEAD_ACTIONS: Final = frozenset(
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
JUMP_SQUAT_FRAMES: Final[dict[Character, int]] = {
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

# DESNOTE(jbarber, 2026-08-17): 17.1 degrees is the documented request-space
# boundary. Keep hardware/game integer-stick quantization outside this API, but
# clamp one representable float inward so trigonometric roundoff cannot cross the
# montage's accepted interval. See https://www.ssbwiki.com/Wavedash#Lengths
WAVEDASH_MIN_ANGLE_DEGREES: Final = 17.1
WAVEDASH_MAX_ANGLE_DEGREES: Final = 90.0
_WAVEDASH_MIN_SAFE_ANGLE_DEGREES: Final = math.nextafter(WAVEDASH_MIN_ANGLE_DEGREES, WAVEDASH_MAX_ANGLE_DEGREES)
_WAVEDASH_MAX_SAFE_ANGLE_DEGREES: Final = math.nextafter(WAVEDASH_MAX_ANGLE_DEGREES, WAVEDASH_MIN_ANGLE_DEGREES)
_WAVEDASH_MIN_ROUNDOFF_ANGLE_DEGREES: Final = math.nextafter(WAVEDASH_MIN_ANGLE_DEGREES, -math.inf)
_WAVEDASH_MAX_ROUNDOFF_ANGLE_DEGREES: Final = math.nextafter(WAVEDASH_MAX_ANGLE_DEGREES, math.inf)


def player(player_state: CharacterState) -> PlayerState | None:
    return player_state.player()


def is_interrupted(player_state: CharacterState, player_state_value: PlayerState, *, include_hitlag: bool) -> bool:
    status = player_state.get_state()
    return (
        player_state_value.action in DEAD_ACTIONS
        or (include_hitlag and status is CharacterStatus.HitLag)
        or status in {CharacterStatus.Hitstun, CharacterStatus.GrabbedByEnemy, CharacterStatus.ShieldBroken}
    )


def validate_button(button: Button, allowed: frozenset[Button], name: str) -> None:
    if button not in allowed:
        choices = ", ".join(sorted(item.name for item in allowed))
        raise ValueError(f"{name} must be one of: {choices}")


def clamp_wavedash_angle(angle_degrees: float) -> float:
    if not math.isfinite(angle_degrees):
        raise ValueError("angle_degrees must be finite")
    if not (_WAVEDASH_MIN_ROUNDOFF_ANGLE_DEGREES <= angle_degrees <= _WAVEDASH_MAX_ROUNDOFF_ANGLE_DEGREES):
        raise ValueError("angle_degrees must be between 17.1 and 90")
    return min(_WAVEDASH_MAX_SAFE_ANGLE_DEGREES, max(_WAVEDASH_MIN_SAFE_ANGLE_DEGREES, angle_degrees))


def apply_wavedash_input(
    controls: SimpleControls,
    direction: WavedashDirection,
    angle_degrees: float,
    dodge_button: Button,
) -> None:
    controls.release_all()
    if direction is WavedashDirection.Right:
        controls.tilt_stick(StickReferenceAxis.RIGHT, -angle_degrees)
    else:
        controls.tilt_stick(StickReferenceAxis.LEFT, angle_degrees)
    controls.press_button(dodge_button)
