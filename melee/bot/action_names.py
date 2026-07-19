"""Resolve libmelee action states to human-readable Melee move names."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib.resources import files
from typing import Final, TypedDict, cast

from melee.enums import Action, Character
from melee.gamestate import UnknownAnimation

_ACTION_STATE_PATH = files("melee.bot.data") / "ssbm_action_state.json"


class _ActionStateEntry(TypedDict):
    ident: str


class _ActionStateSection(TypedDict):
    known_values: dict[str, _ActionStateEntry]


_CHARACTER_SECTION: Final[dict[Character, str]] = {
    Character.MARIO: "Mario",
    Character.FOX: "Fox",
    Character.CPTFALCON: "CaptainFalcon",
    Character.DK: "DonkeyKong",
    Character.KIRBY: "Kirby",
    Character.BOWSER: "Bowser",
    Character.LINK: "Link",
    Character.SHEIK: "Sheik",
    Character.NESS: "Ness",
    Character.PEACH: "Peach",
    Character.POPO: "Popo",
    Character.PIKACHU: "Pikachu",
    Character.SAMUS: "Samus",
    Character.YOSHI: "Yoshi",
    Character.JIGGLYPUFF: "Jigglypuff",
    Character.MEWTWO: "Mewtwo",
    Character.LUIGI: "Luigi",
    Character.MARTH: "Marth",
    Character.ZELDA: "Zelda",
    Character.YLINK: "YoungLink",
    Character.DOC: "DrMario",
    Character.FALCO: "Falco",
    Character.PICHU: "Pichu",
    Character.GAMEANDWATCH: "GameAndWatch",
    Character.GANONDORF: "Ganondorf",
    Character.ROY: "Roy",
}

_COMMON_ATTACK_NAMES: Final[dict[str, str]] = {
    "ATTACK_11": "Jab",
    "ATTACK_12": "Jab",
    "ATTACK_13": "Jab",
    "ATTACK_100_START": "Rapid Jabs",
    "ATTACK_100_LOOP": "Rapid Jabs",
    "ATTACK_100_END": "Rapid Jabs",
    "ATTACK_DASH": "Dash Attack",
    "ATTACK_S_3_HI": "Forward Tilt",
    "ATTACK_S_3_HI_S": "Forward Tilt",
    "ATTACK_S_3_S": "Forward Tilt",
    "ATTACK_S_3_LW_S": "Forward Tilt",
    "ATTACK_S_3_LW": "Forward Tilt",
    "ATTACK_HI_3": "Up Tilt",
    "ATTACK_LW_3": "Down Tilt",
    "ATTACK_S_4_HI": "Forward Smash",
    "ATTACK_S_4_HI_S": "Forward Smash",
    "ATTACK_S_4_S": "Forward Smash",
    "ATTACK_S_4_LW_S": "Forward Smash",
    "ATTACK_S_4_LW": "Forward Smash",
    "ATTACK_HI_4": "Up Smash",
    "ATTACK_LW_4": "Down Smash",
    "ATTACK_AIR_N": "Neutral Air",
    "ATTACK_AIR_F": "Forward Air",
    "ATTACK_AIR_B": "Back Air",
    "ATTACK_AIR_HI": "Up Air",
    "ATTACK_AIR_LW": "Down Air",
    "LANDING_AIR_N": "Neutral Air (landing)",
    "LANDING_AIR_F": "Forward Air (landing)",
    "LANDING_AIR_B": "Back Air (landing)",
    "LANDING_AIR_HI": "Up Air (landing)",
    "LANDING_AIR_LW": "Down Air (landing)",
    "DOWN_ATTACK_U": "Getup Attack",
    "DOWN_ATTACK_D": "Getup Attack",
    "CLIFF_ATTACK_SLOW": "Ledge Attack",
    "CLIFF_ATTACK_QUICK": "Ledge Attack",
    "CATCH_ATTACK": "Pummel",
    "THROW_F": "Forward Throw",
    "THROW_B": "Back Throw",
    "THROW_HI": "Up Throw",
    "THROW_LW": "Down Throw",
}

# Longest tokens first so e.g. GROUND_STARTUP is stripped before GROUND.
_IDENT_SUFFIX_TOKENS: Final[tuple[str, ...]] = (
    "GROUND_STARTUP",
    "AIR_STARTUP",
    "GROUND_LOOP",
    "AIR_LOOP",
    "GROUND_END",
    "AIR_END",
    "GROUND_ENDING",
    "AIR_ENDING",
    "GROUND_REFLECT",
    "AIR_REFLECT",
    "FULLY_CHARGED",
    "FULL_CHARGE",
    "CHARGE_STARTUP",
    "CHARGE_LOOP",
    "CHARGE_STOP",
    "CHARGE_RELEASE",
    "START_CHARGE",
    "CHANGE_DIRECTION",
    "BOUNCE_END",
    "TAKEOFF",
    "HIT_WALL",
    "GROUND",
    "AIR",
    "RIGHT",
    "LEFT",
    "STARTUP",
    "LOOP",
    "ENDING",
    "END",
    "HIT",
    "CHARGE",
    "START",
    "STOP",
    "REFLECT",
)

_TRAILING_STEP_RE = re.compile(r"_\d+$")


@lru_cache(maxsize=1)
def _load_action_state() -> dict[str, _ActionStateSection]:
    return cast(
        dict[str, _ActionStateSection],
        json.loads(_ACTION_STATE_PATH.read_text(encoding="utf-8")),
    )


def _lookup_ident(character: Character, action_id: int) -> str | None:
    data = _load_action_state()
    action_key = str(action_id)
    if action_id <= 340:
        common = data.get("Common")
        if common is not None:
            entry = common["known_values"].get(action_key)
            if entry is not None:
                return entry["ident"]
    section_name = _CHARACTER_SECTION.get(character)
    if section_name is None:
        return None
    section = data.get(section_name)
    if section is None:
        return None
    entry = section["known_values"].get(action_key)
    return entry["ident"] if entry is not None else None


def _title_case_ident(ident: str) -> str:
    return " ".join(part.capitalize() for part in ident.split("_") if part)


def _format_action_ident(ident: str) -> str:
    common_name = _COMMON_ATTACK_NAMES.get(ident)
    if common_name is not None:
        return common_name

    normalized = ident
    changed = True
    while changed:
        changed = False
        for token in _IDENT_SUFFIX_TOKENS:
            suffix = f"_{token}"
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
                changed = True
                break
        trimmed = _TRAILING_STEP_RE.sub("", normalized)
        if trimmed != normalized:
            normalized = trimmed
            changed = True

    if not normalized:
        return _title_case_ident(ident)
    return _title_case_ident(normalized)


def action_name(
    character: Character,
    action: Action | UnknownAnimation,
) -> str:
    """Return a human-readable move name for ``character``'s current action."""
    if isinstance(action, UnknownAnimation):
        return f"unknown action ({action.value})"

    ident = action_state_ident(character, int(action.value))
    if ident is None:
        return _title_case_ident(action.name)
    return _format_action_ident(ident)


def character_section_name(character: Character) -> str | None:
    """Return the ssbm-data action_state.json section name for ``character``."""
    return _CHARACTER_SECTION.get(character)


def action_state_ident(character: Character, action_id: int) -> str | None:
    """Return the raw ssbm-data ident for ``character``'s ``action_id``."""
    return _lookup_ident(character, action_id)
