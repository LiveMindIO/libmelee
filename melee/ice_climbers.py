"""Derive Ice Climbers partner state from normal Slippi frame data."""

from __future__ import annotations

import math
from typing import Final

from melee import enums
from melee.gamestate import GameState, PlayerState

# DESNOTE(jbarber, 2026-09-11): Melee's Nana follower logic uses a literal
# 25-unit distance and Popo's common mid-walk attribute as the maximum relative
# per-frame displacement. The latter is 0.47 at PlPp.dat offset 0x32B4 in the
# GALE01 Rev. 2 DAT whose SHA-256 is
# 5dd044b2ac5003f18dfca6e3a5197724f383419b4fc31bd4cb0a6205052507c0.
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_0A01.c#L7569-L7653
NANA_FOLLOW_DISTANCE: Final = 25.0
NANA_FOLLOW_MAX_RELATIVE_SPEED: Final = 0.47

# DESNOTE(jbarber, 2026-09-11): These are the big-endian floats at PlPp.dat
# offsets 0x34A4 (special attribute x7C) and 0x34F8 (xD0) in the same DAT.
# Their consumers are documented in the pinned Belay and Squall sources:
# https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftPopo/ftPp_SpecialHi.c#L201-L217
# https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftNana/ftNn_SpecialS.c#L45-L103
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
        if popo.character is not enums.Character.POPO or nana is None or nana.character is not enums.Character.NANA:
            continue

        distance_squared = _vector_difference_squared(
            popo.position.x,
            popo.position.y,
            nana.position.x,
            nana.position.y,
        )
        if not math.isfinite(distance_squared):
            continue
        previous_popo = _compatible_previous_popo(
            gamestate,
            previous_gamestate,
            previous_gamestate.players.get(port),
        )
        previous_mode = previous_popo.nana_mode if previous_popo is not None else None

        if previous_mode is enums.NanaMode.FOLLOWER:
            # DESNOTE(jbarber, 2026-09-11): Melee preserves follower mode at
            # exactly 25 units and exits only above it or during Nana's Popo
            # Up-B states 361-366.
            # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_0A01.c#L7615-L7653
            exits_follower_mode = _is_nana_in_popo_up_b(nana) or distance_squared > NANA_FOLLOW_DISTANCE**2
            popo.nana_mode = enums.NanaMode.CPU_RETURNING if exits_follower_mode else enums.NanaMode.FOLLOWER
        else:
            popo.nana_mode = (
                enums.NanaMode.FOLLOWER
                if previous_popo is not None
                and _can_enter_follower_mode(
                    popo,
                    nana,
                    previous_popo,
                    distance_squared,
                )
                else enums.NanaMode.CPU_RETURNING
            )

        # DESNOTE(jbarber, 2026-09-11): The hidden hit-source nibble cannot be
        # reconstructed from Slippi, while x2219_b5 is approximated by its
        # emitted hitlag state. See the pinned Belay source linked above and
        # https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftNana/ftNn_Init.c#L394-L425
        popo.nana_belay_eligible = (
            nana.hitlag_left <= 0 and not nana.is_defender_in_hitlag and distance_squared < NANA_BELAY_RADIUS**2
        )

        # Melee truncates both squared values to signed integers before the
        # strict Squall comparison. Slippi does not expose Popo's runtime scale,
        # so this uses the normal-scale tournament value.
        popo.nana_squall_hammer_eligible = int(distance_squared) < int(NANA_SQUALL_HAMMER_RADIUS**2)


def _compatible_previous_popo(
    gamestate: GameState,
    previous_gamestate: GameState,
    previous_popo: PlayerState | None,
) -> PlayerState | None:
    if (
        previous_gamestate.frame != gamestate.frame - 1
        or previous_popo is None
        or previous_popo.character is not enums.Character.POPO
        or previous_popo.nana is None
        or previous_popo.nana.character is not enums.Character.NANA
    ):
        return None
    return previous_popo


def _can_enter_follower_mode(
    popo: PlayerState,
    nana: PlayerState,
    previous_popo: PlayerState,
    distance_squared: float,
) -> bool:
    previous_nana = previous_popo.nana
    assert previous_nana is not None

    # DESNOTE(jbarber, 2026-09-11): Melee requires both climbers grounded,
    # rejects Popo Up-B, then checks Nana-vs-Popo pos_delta and the strict
    # 25-unit distance. Slippi omits the remaining CPU flags.
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_0A01.c#L7578-L7613
    if (
        not popo.on_ground
        or not nana.on_ground
        or _is_nana_in_popo_up_b(nana)
        or nana.hitlag_left > 0
        or nana.hitstun_frames_left > 1
        or distance_squared >= NANA_FOLLOW_DISTANCE**2
    ):
        return False

    # DESNOTE(jbarber, 2026-09-11): Melee's pos_delta is current position minus
    # previous position. Reconstructing it from consecutive Slippi positions is
    # exact; summing exported velocity fields omits nudge, shield knockback,
    # moving-platform, and wind displacement.
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/fighter.c#L1444-L1453
    nana_delta_x = nana.position.x - previous_nana.position.x
    nana_delta_y = nana.position.y - previous_nana.position.y
    popo_delta_x = popo.position.x - previous_popo.position.x
    popo_delta_y = popo.position.y - previous_popo.position.y
    relative_movement_squared = _vector_difference_squared(
        nana_delta_x,
        nana_delta_y,
        popo_delta_x,
        popo_delta_y,
    )
    return relative_movement_squared <= NANA_FOLLOW_MAX_RELATIVE_SPEED**2


def _vector_difference_squared(
    first_x: float,
    first_y: float,
    second_x: float,
    second_y: float,
) -> float:
    x = first_x - second_x
    y = first_y - second_y
    return x**2 + y**2


def _is_nana_in_popo_up_b(nana: PlayerState) -> bool:
    return _NANA_POPO_UP_B_FIRST <= nana.action.value <= _NANA_POPO_UP_B_LAST
