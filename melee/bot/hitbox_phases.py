"""Verified combat phases, independent of historical CSV geometry slots.

Geometry is a static unblended pose, not a full engine collision simulation.
Only explicitly curated phases have sweet/sour labels. Absence of a label
does not mean a move has no sweetspot. IDs are scoped to character/action.
"""

import json
from dataclasses import dataclass
from functools import cache, lru_cache
from importlib.resources import files
from typing import Literal

from melee.enums import Action, Character

Spot = Literal["sweet", "sour"]

# Reviewed NTSC 1.02 phase signatures. Each entry binds character, runtime
# action, engine hitbox ID, bone, inclusive frames, damage, angle, and element.
# These named knee/tipper/hilt/lightning variants are not a global strength
# ranking. A signature mismatch intentionally leaves the phase unlabeled.
_CURATED_PHASES = {
    (Character.CPTFALCON, Action.FAIR, 0, 7, 14, 16, 18, 32, 2): ("sweet", "early knee"),
    (Character.CPTFALCON, Action.FAIR, 1, 4, 14, 16, 18, 32, 2): ("sweet", "early knee"),
    (Character.CPTFALCON, Action.FAIR, 0, 7, 17, 30, 6, 361, 0): ("sour", "late knee"),
    (Character.CPTFALCON, Action.FAIR, 1, 4, 17, 30, 6, 361, 0): ("sour", "late knee"),
    (Character.MARTH, Action.FSMASH_MID, 3, 76, 10, 13, 20, 361, 3): ("sweet", "tipper"),
    (Character.MARTH, Action.FSMASH_MID, 0, 76, 10, 13, 14, 361, 3): ("sour", "non-tipper"),
    (Character.MARTH, Action.FSMASH_MID, 1, 71, 10, 13, 14, 361, 3): ("sour", "non-tipper"),
    (Character.MARTH, Action.FSMASH_MID, 2, 4, 10, 13, 14, 361, 3): ("sour", "non-tipper"),
    (Character.MARTH, Action.FAIR, 3, 76, 4, 7, 13, 67, 3): ("sweet", "tipper"),
    (Character.MARTH, Action.FAIR, 0, 76, 4, 7, 10, 361, 3): ("sour", "non-tipper"),
    (Character.MARTH, Action.FAIR, 1, 71, 4, 7, 9, 361, 3): ("sour", "non-tipper"),
    (Character.MARTH, Action.FAIR, 2, 25, 4, 7, 9, 361, 3): ("sour", "non-tipper"),
    (Character.ROY, Action.FSMASH_MID, 0, 78, 12, 14, 20, 361, 3): ("sweet", "hilt"),
    (Character.ROY, Action.FSMASH_MID, 1, 73, 12, 14, 20, 361, 3): ("sweet", "hilt"),
    (Character.ROY, Action.FSMASH_MID, 2, 4, 12, 14, 20, 361, 3): ("sweet", "hilt"),
    (Character.ROY, Action.FSMASH_MID, 3, 78, 12, 14, 12, 361, 0): ("sour", "blade tip"),
    (Character.ZELDA, Action.FAIR, 2, 10, 8, 11, 20, 361, 2): ("sweet", "lightning kick"),
    (Character.ZELDA, Action.FAIR, 0, 7, 8, 11, 10, 361, 0): ("sour", "non-lightning kick"),
    (Character.ZELDA, Action.FAIR, 1, 4, 8, 11, 10, 361, 0): ("sour", "non-lightning kick"),
}


class HitboxPhaseError(ValueError):
    """Phase selection or verified data is unavailable."""


@dataclass(frozen=True)
class HitboxCombat:
    damage: int
    angle: int
    knockback_growth: int
    weight_set_knockback: int
    base_knockback: int
    element: int
    shield_damage: int
    hits_grounded: bool
    hits_aerial: bool
    hit_group: int


@dataclass(frozen=True)
class HitboxFrame:
    frame: int
    x: float
    y: float
    z: float
    radius: float


@dataclass(frozen=True)
class HitboxPhase:
    phase_id: str
    start_frame: int
    end_frame: int
    combat: HitboxCombat
    frames: tuple[HitboxFrame, ...]
    spot: Spot | None = None
    label: str | None = None


@dataclass(frozen=True)
class ActionHitbox:
    action_id: int
    hitbox_id: int
    bone_id: int
    phases: tuple[HitboxPhase, ...]


@lru_cache(maxsize=1)
def _catalog():
    return json.loads(files("melee").joinpath("hitbox_catalog.json").read_text())


@cache
def _action_hitboxes(character: Character, action: Action) -> tuple[ActionHitbox, ...]:
    key = f"{character.value}:{action.value}"
    catalog = _catalog()
    if key in catalog["unavailable"]:
        raise HitboxPhaseError(f"verified hitbox geometry unavailable for {character.name} action {action.value}")
    groups = []
    for group in catalog["actions"].get(key, []):
        phases = []
        for phase in group["phases"]:
            combat = phase["combat"]
            signature = (
                character,
                action,
                group["hitbox_id"],
                group["bone_id"],
                phase["start_frame"],
                phase["end_frame"],
                combat["damage"],
                combat["angle"],
                combat["element"],
            )
            spot, label = _CURATED_PHASES.get(signature, (None, None))
            phases.append(
                HitboxPhase(
                    phase["phase_id"],
                    phase["start_frame"],
                    phase["end_frame"],
                    HitboxCombat(**{name: combat[name] for name in HitboxCombat.__dataclass_fields__}),
                    tuple(HitboxFrame(*frame) for frame in phase["frames"]),
                    spot,
                    label,
                )
            )
        groups.append(ActionHitbox(action.value, group["hitbox_id"], group["bone_id"], tuple(phases)))
    return tuple(groups)


def select_hitbox_phases(
    character: Character,
    action: Action,
    *,
    hitbox_id: int | None = None,
    phase_id: str | None = None,
    spot: Spot | None = None,
) -> tuple[ActionHitbox, ...]:
    """Select exact physical hitbox phases without guessing CSV-slot mappings.

    An explicit selection with no matches raises, including uncurated spots.
    Unfiltered actions without fighter-owned hitboxes return an empty tuple.
    """
    if spot not in (None, "sweet", "sour"):
        raise HitboxPhaseError("spot must be sweet or sour")
    groups = []
    for group in _action_hitboxes(character, action):
        if hitbox_id is not None and group.hitbox_id != hitbox_id:
            continue
        phases = tuple(
            p for p in group.phases if (phase_id is None or p.phase_id == phase_id) and (spot is None or p.spot == spot)
        )
        if phases:
            groups.append(ActionHitbox(group.action_id, group.hitbox_id, group.bone_id, phases))
    if not groups and any(v is not None for v in (hitbox_id, phase_id, spot)):
        raise HitboxPhaseError(f"no verified phases match {character.name} action {action.value}")
    return tuple(groups)


def get_hitbox_phases(
    character_query: str | int,
    action_query: str | int,
    *,
    hitbox_id: int | None = None,
    phase_id: str | None = None,
    spot: Spot | None = None,
) -> tuple[ActionHitbox, ...]:
    """Resolve the same query aliases as get_framedata and return combat phases."""
    from melee.bot.framedata_query import resolve_actions, resolve_character

    character = resolve_character(character_query)
    actions = resolve_actions(character, action_query)
    groups = tuple(
        group
        for entry in actions
        for group in select_hitbox_phases(character, entry.action)
        if hitbox_id is None or group.hitbox_id == hitbox_id
    )
    if spot not in (None, "sweet", "sour"):
        raise HitboxPhaseError("spot must be sweet or sour")
    result = tuple(
        ActionHitbox(
            g.action_id,
            g.hitbox_id,
            g.bone_id,
            tuple(
                p for p in g.phases if (phase_id is None or p.phase_id == phase_id) and (spot is None or p.spot == spot)
            ),
        )
        for g in groups
    )
    result = tuple(g for g in result if g.phases)
    if not result and any(v is not None for v in (hitbox_id, phase_id, spot)):
        raise HitboxPhaseError("no verified hitbox phases match this query")
    return result


def get_sweetspots(character_query: str | int, action_query: str | int) -> tuple[ActionHitbox, ...]:
    return get_hitbox_phases(character_query, action_query, spot="sweet")


def get_sourspots(character_query: str | int, action_query: str | int) -> tuple[ActionHitbox, ...]:
    return get_hitbox_phases(character_query, action_query, spot="sour")
