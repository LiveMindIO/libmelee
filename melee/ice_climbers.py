"""Derive Ice Climbers partner state from normal Slippi frame data."""

from __future__ import annotations

import math
from typing import Final

from melee import enums
from melee.gamestate import GameState, PlayerState

NANA_FOLLOW_DISTANCE: Final = 25.0
NANA_FOLLOW_MAX_RELATIVE_SPEED: Final = 0.47
NANA_BELAY_RADIUS: Final = 60.0
NANA_SQUALL_HAMMER_RADIUS: Final = 20.0

_NANA_POPO_UP_B_FIRST = 361
_NANA_POPO_UP_B_LAST = 366


def derive_ice_climbers_state(
    gamestate: GameState,
    previous_gamestate: GameState,
) -> None:
    """Populate inferred Nana mode and partner-special eligibility.

    Normal Slippi frames expose both climbers' positions, movement, actions, and
    hitlag, but not Melee's follower bit or every internal recruitment flag. The
    derivation preserves the thresholds applied by this heuristic while
    approximating the omitted follower and CPU-state gates.
    """
    for port, popo in gamestate.players.items():
        popo.nana_mode = None
        popo.nana_belay_eligible = None
        popo.nana_squall_hammer_eligible = None

        nana = popo.nana
        if (
            popo.character is not enums.Character.POPO
            or nana is None
            or nana.character is not enums.Character.NANA
        ):
            continue

        distance_squared = _distance_squared(popo, nana)
        if not math.isfinite(distance_squared):
            continue
        previous_popo = previous_gamestate.players.get(port)
        previous_mode = _compatible_previous_mode(
            gamestate,
            previous_gamestate,
            previous_popo,
        )

        if previous_mode is enums.NanaMode.FOLLOWER:
            exits_follower_mode = (
                _is_nana_popo_up_b(nana)
                or distance_squared > NANA_FOLLOW_DISTANCE**2
            )
            popo.nana_mode = (
                enums.NanaMode.CPU_RETURNING
                if exits_follower_mode
                else enums.NanaMode.FOLLOWER
            )
        else:
            popo.nana_mode = (
                enums.NanaMode.FOLLOWER
                if _can_enter_follower_mode(popo, nana, distance_squared)
                else enums.NanaMode.CPU_RETURNING
            )

        # DESNOTE(jbarber, 2026-09-11): These radii are the big-endian floats at
        # PlPp.dat offsets 0x34A4 and 0x34F8 in GALE01 Rev. 2. The extracted DAT
        # SHA-256 is 5dd044b2ac5003f18dfca6e3a5197724f383419b4fc31bd4cb0a6205052507c0.
        # The hidden hit-source nibble cannot be reconstructed from Slippi, while
        # x2219_b5 is approximated by its emitted hitlag state.
        # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftPopo/ftPp_SpecialHi.c#L201-L217
        popo.nana_belay_eligible = (
            nana.hitlag_left <= 0
            and not nana.is_defender_in_hitlag
            and distance_squared < NANA_BELAY_RADIUS**2
        )

        # Melee truncates both squared values to signed integers before the
        # strict Squall comparison. Slippi does not expose Popo's runtime scale,
        # so this uses the normal-scale tournament value.
        popo.nana_squall_hammer_eligible = int(distance_squared) < int(
            NANA_SQUALL_HAMMER_RADIUS**2
        )


def _compatible_previous_mode(
    gamestate: GameState,
    previous_gamestate: GameState,
    previous_popo: PlayerState | None,
) -> enums.NanaMode | None:
    if (
        previous_gamestate.frame != gamestate.frame - 1
        or previous_popo is None
        or previous_popo.character is not enums.Character.POPO
        or previous_popo.nana is None
        or previous_popo.nana.character is not enums.Character.NANA
    ):
        return None
    return previous_popo.nana_mode


def _can_enter_follower_mode(
    popo: PlayerState,
    nana: PlayerState,
    distance_squared: float,
) -> bool:
    if (
        not popo.on_ground
        or not nana.on_ground
        or _is_nana_popo_up_b(nana)
        or nana.hitlag_left > 0
        or nana.hitstun_frames_left > 1
        or distance_squared >= NANA_FOLLOW_DISTANCE**2
    ):
        return False

    relative_x = _horizontal_speed(nana) - _horizontal_speed(popo)
    relative_y = _vertical_speed(nana) - _vertical_speed(popo)
    return relative_x**2 + relative_y**2 <= NANA_FOLLOW_MAX_RELATIVE_SPEED**2


def _distance_squared(first: PlayerState, second: PlayerState) -> float:
    x = first.position.x - second.position.x
    y = first.position.y - second.position.y
    return x**2 + y**2


def _horizontal_speed(player: PlayerState) -> float:
    return player.speed_air_x_self + player.speed_ground_x_self + player.speed_x_attack


def _vertical_speed(player: PlayerState) -> float:
    return player.speed_y_self + player.speed_y_attack


def _is_nana_popo_up_b(nana: PlayerState) -> bool:
    return _NANA_POPO_UP_B_FIRST <= nana.action.value <= _NANA_POPO_UP_B_LAST
