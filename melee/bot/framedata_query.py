"""Query libmelee framedata for bot-author agents and tooling."""

from __future__ import annotations

import csv
import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final, TextIO, TypedDict

import melee
from melee.enums import Action, AttackState, Character
from melee.framedata import FrameData

from melee.bot.action_names import (
    action_name,
    action_state_ident,
    character_section_name,
)

_MAX_CSV_ROWS: Final[int] = 200
_SPECIAL_SLOT_ORDER: Final[tuple[str, ...]] = (
    "neutral-special",
    "side-special",
    "up-special",
    "down-special",
)
_SPECIAL_SLOT_ALIASES: Final[dict[str, str]] = {
    "neutral-special": "neutral-special",
    "neutral special": "neutral-special",
    "neutral-b": "neutral-special",
    "neutral b": "neutral-special",
    "b-neutral": "neutral-special",
    "side-special": "side-special",
    "side special": "side-special",
    "side-b": "side-special",
    "side b": "side-special",
    "b-side": "side-special",
    "up-special": "up-special",
    "up special": "up-special",
    "up-b": "up-special",
    "up b": "up-special",
    "b-up": "up-special",
    "down-special": "down-special",
    "down special": "down-special",
    "down-b": "down-special",
    "down b": "down-special",
    "b-down": "down-special",
}
_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
_SPECIAL_SLOT_BY_NORMALIZED: Final[dict[str, str]] = {
    _NORMALIZE_RE.sub("", alias.strip().lower()): slot
    for alias, slot in _SPECIAL_SLOT_ALIASES.items()
}
_CHARACTER_ALIASES: Final[dict[str, Character]] = {
    "mario": Character.MARIO,
    "fox": Character.FOX,
    "captain_falcon": Character.CPTFALCON,
    "captainfalcon": Character.CPTFALCON,
    "falcon": Character.CPTFALCON,
    "cptfalcon": Character.CPTFALCON,
    "donkey_kong": Character.DK,
    "donkeykong": Character.DK,
    "dk": Character.DK,
    "kirby": Character.KIRBY,
    "bowser": Character.BOWSER,
    "link": Character.LINK,
    "sheik": Character.SHEIK,
    "ness": Character.NESS,
    "peach": Character.PEACH,
    "ice_climbers": Character.POPO,
    "iceclimbers": Character.POPO,
    "popo": Character.POPO,
    "pikachu": Character.PIKACHU,
    "samus": Character.SAMUS,
    "yoshi": Character.YOSHI,
    "jigglypuff": Character.JIGGLYPUFF,
    "puff": Character.JIGGLYPUFF,
    "mewtwo": Character.MEWTWO,
    "luigi": Character.LUIGI,
    "marth": Character.MARTH,
    "zelda": Character.ZELDA,
    "young_link": Character.YLINK,
    "younglink": Character.YLINK,
    "ylink": Character.YLINK,
    "dr_mario": Character.DOC,
    "drmario": Character.DOC,
    "doc": Character.DOC,
    "falco": Character.FALCO,
    "pichu": Character.PICHU,
    "mr_game_and_watch": Character.GAMEANDWATCH,
    "gameandwatch": Character.GAMEANDWATCH,
    "ganondorf": Character.GANONDORF,
    "roy": Character.ROY,
}


class FramedataQueryError(ValueError):
    """Raised when character or action resolution fails."""


class FramedataFrame(TypedDict):
    hitbox_1_status: bool
    hitbox_1_size: float
    hitbox_1_x: float
    hitbox_1_y: float
    hitbox_2_status: bool
    hitbox_2_size: float
    hitbox_2_x: float
    hitbox_2_y: float
    hitbox_3_status: bool
    hitbox_3_size: float
    hitbox_3_x: float
    hitbox_3_y: float
    hitbox_4_status: bool
    hitbox_4_size: float
    hitbox_4_x: float
    hitbox_4_y: float
    locomotion_x: float
    locomotion_y: float
    iasa: bool
    facing_changed: bool
    projectile: bool


@dataclass(frozen=True)
class ResolvedAction:
    action: Action
    action_id: int
    action_enum: str
    action_label: str
    action_state: str | None


@lru_cache(maxsize=1)
def _frame_data() -> FrameData:
    return FrameData()


def _open_framedata_csv() -> TextIO:
    package_csv = Path(melee.__file__).resolve().parent / "framedata.csv"
    if package_csv.is_file():
        return package_csv.open(newline="")
    legacy = Path(__file__).resolve().parents[2] / "vendor/libmelee/melee/framedata.csv"
    if legacy.is_file():
        return legacy.open(newline="")
    msg = "framedata.csv is missing from the installed melee package"
    raise FramedataQueryError(msg)


def _normalize_token(value: str) -> str:
    return _NORMALIZE_RE.sub("", value.strip().lower())


def resolve_character(character: str | int) -> Character:
    if isinstance(character, int):
        return Character(character)
    token = character.strip()
    if token.isdigit():
        return Character(int(token))
    normalized = _normalize_token(token)
    if normalized in _CHARACTER_ALIASES:
        return _CHARACTER_ALIASES[normalized]
    for melee_character in Character:
        section = character_section_name(melee_character)
        if section is not None and _normalize_token(section) == normalized:
            return melee_character
    for melee_character in Character:
        if _normalize_token(melee_character.name) == normalized:
            return melee_character
    msg = f"unknown character: {character!r}"
    raise FramedataQueryError(msg)


def _is_bmove(character: Character, action: Action) -> bool:
    # DESNOTE(jbarber, 2026-07-07): libmelee FrameData.is_bmove references
    # Action.UNKNOWN_ANIMATION, which this fork does not define; mirror the
    # value check and Peach exceptions locally.
    if character == Character.PEACH and action in (
        Action.LASER_GUN_PULL,
        Action.NEUTRAL_B_CHARGING,
        Action.NEUTRAL_B_ATTACKING,
    ):
        return False
    if character == Character.PEACH and action in (
        Action.SWORD_DANCE_2_MID,
        Action.SWORD_DANCE_1,
        Action.SWORD_DANCE_2_HIGH,
    ):
        return False
    return action.value >= Action.LASER_GUN_PULL.value


def _resolve_action_entry(character: Character, action: Action) -> ResolvedAction:
    action_id = int(action.value)
    return ResolvedAction(
        action=action,
        action_id=action_id,
        action_enum=action.name,
        action_label=action_name(character, action),
        action_state=action_state_ident(character, action_id),
    )


def _special_slot_groups(character: Character) -> list[tuple[str, list[ResolvedAction]]]:
    frame_data = _frame_data()
    grouped: dict[str, list[ResolvedAction]] = {}
    for action in frame_data.framedata[character]:
        if not _is_bmove(character, action):
            continue
        entry = _resolve_action_entry(character, action)
        grouped.setdefault(entry.action_label, []).append(entry)
    ordered = sorted(
        grouped.items(),
        key=lambda item: min(resolved.action_id for resolved in item[1]),
    )
    return [(label, sorted(entries, key=lambda entry: entry.action_id)) for label, entries in ordered]


def _resolve_special_slot(character: Character, slot: str) -> list[ResolvedAction]:
    normalized = _SPECIAL_SLOT_BY_NORMALIZED.get(_normalize_token(slot))
    if normalized is None:
        msg = f"unknown special slot: {slot!r}"
        raise FramedataQueryError(msg)
    groups = _special_slot_groups(character)
    try:
        index = _SPECIAL_SLOT_ORDER.index(normalized)
    except ValueError as exc:
        raise FramedataQueryError(f"unknown special slot: {slot!r}") from exc
    if index >= len(groups):
        msg = (
            f"{character.name} has no {_SPECIAL_SLOT_ORDER[index]!r} "
            f"(only {len(groups)} special groups)"
        )
        raise FramedataQueryError(msg)
    return groups[index][1]


def _match_actions_by_label(character: Character, query: str) -> list[ResolvedAction]:
    normalized = _normalize_token(query)
    frame_data = _frame_data()
    matches: list[ResolvedAction] = []
    for action in frame_data.framedata[character]:
        entry = _resolve_action_entry(character, action)
        candidates = {
            _normalize_token(entry.action_label),
            _normalize_token(entry.action_enum),
            _normalize_token(entry.action_state or ""),
        }
        if normalized in candidates:
            matches.append(entry)
    if not matches:
        for action in frame_data.framedata[character]:
            entry = _resolve_action_entry(character, action)
            candidates = (
                _normalize_token(entry.action_label),
                _normalize_token(entry.action_enum),
                _normalize_token(entry.action_state or ""),
            )
            if any(normalized in candidate for candidate in candidates if candidate):
                matches.append(entry)
    return sorted(matches, key=lambda entry: entry.action_id)


def resolve_actions(character: Character, action_query: str | int) -> list[ResolvedAction]:
    frame_data = _frame_data()
    if isinstance(action_query, int):
        action = Action(action_query)
        if not frame_data.framedata[character].get(action):
            msg = f"no framedata for {character.name} action id {action_query}"
            raise FramedataQueryError(msg)
        return [_resolve_action_entry(character, action)]

    token = action_query.strip()
    if token.isdigit():
        return resolve_actions(character, int(token))

    normalized = _normalize_token(token)
    slot = _SPECIAL_SLOT_BY_NORMALIZED.get(normalized)
    if slot is not None:
        return _resolve_special_slot(character, slot)

    try:
        enum_action = Action[token.upper()]
    except KeyError:
        enum_action = None
    else:
        if frame_data.framedata[character].get(enum_action):
            return [_resolve_action_entry(character, enum_action)]

    label_matches = _match_actions_by_label(character, token)
    if label_matches:
        return label_matches

    msg = f"unknown action for {character.name}: {action_query!r}"
    raise FramedataQueryError(msg)


def _hitbox_bounds(x: float, size: float) -> tuple[float, float]:
    return x - size, x + size


def _frame_hitboxes(frame: FramedataFrame) -> list[dict[str, object]]:
    specs: list[tuple[int, bool, float, float, float]] = [
        (1, frame["hitbox_1_status"], frame["hitbox_1_size"], frame["hitbox_1_x"], frame["hitbox_1_y"]),
        (2, frame["hitbox_2_status"], frame["hitbox_2_size"], frame["hitbox_2_x"], frame["hitbox_2_y"]),
        (3, frame["hitbox_3_status"], frame["hitbox_3_size"], frame["hitbox_3_x"], frame["hitbox_3_y"]),
        (4, frame["hitbox_4_status"], frame["hitbox_4_size"], frame["hitbox_4_x"], frame["hitbox_4_y"]),
    ]
    hitboxes: list[dict[str, object]] = []
    for index, status, size, x, y in specs:
        min_x, max_x = _hitbox_bounds(x, size)
        min_y, max_y = _hitbox_bounds(y, size)
        hitboxes.append(
            {
                "index": index,
                "status": status,
                "hitbox_size": size,
                "x": x,
                "y": y,
                "min_x": min_x,
                "min_y": min_y,
                "max_x": max_x,
                "max_y": max_y,
            }
        )
    return hitboxes


def _frame_signature(
    character: Character,
    action: Action,
    frame_number: int,
    frame: FramedataFrame,
    frame_data: FrameData,
) -> tuple[object, ...]:
    attack = frame_data.attack_state(character, action, frame_number)
    hitboxes = tuple(
        (
            box["status"],
            box["hitbox_size"],
            box["x"],
            box["y"],
        )
        for box in _frame_hitboxes(frame)
    )
    return (
        action_state_ident(character, int(action.value)),
        attack.name,
        round(float(frame["locomotion_x"]), 4),
        round(float(frame["locomotion_y"]), 4),
        hitboxes,
        bool(frame["iasa"]),
        bool(frame["facing_changed"]),
        bool(frame["projectile"]),
    )


def _collect_tags(character: Character, actions: Sequence[ResolvedAction]) -> list[str]:
    frame_data = _frame_data()
    tags: set[str] = set()
    for entry in actions:
        action = entry.action
        if frame_data.is_grab(character, action):
            tags.add("GRAB")
        if _is_bmove(character, action):
            tags.add("B_MOVE")
        if frame_data.is_attack(character, action):
            tags.add("ATTACK")
        if frame_data.is_roll(character, action):
            tags.add("ROLL")
        if frame_data.is_shield(action):
            tags.add("SHIELD")
        if frame_data.iasa(character, action) != -1:
            tags.add("IASA")
        for _, frame in frame_data.framedata[character][action].items():
            if frame and frame["projectile"]:
                tags.add("PROJECTILE")
                break
    return sorted(tags)


def _states_for_action(character: Character, entry: ResolvedAction) -> list[dict[str, object]]:
    frame_data = _frame_data()
    action = entry.action
    frames = sorted(frame_data.framedata[character][action])
    if not frames:
        return []

    states: list[dict[str, object]] = []
    segment_start = frames[0]
    previous_signature = _frame_signature(
        character,
        action,
        segment_start,
        frame_data.framedata[character][action][segment_start],
        frame_data,
    )

    def flush(end_frame: int) -> None:
        sample = frame_data.framedata[character][action][segment_start]
        attack = frame_data.attack_state(character, action, segment_start)
        states.append(
            {
                "action_id": entry.action_id,
                "action_enum": entry.action_enum,
                "action_label": entry.action_label,
                "action_state": entry.action_state,
                "start_frame": segment_start,
                "end_frame": end_frame,
                "attack_state": None
                if attack == AttackState.NOT_ATTACKING
                else attack.name,
                "locomotion_x": float(sample["locomotion_x"]),
                "locomotion_y": float(sample["locomotion_y"]),
                "iasa": bool(sample["iasa"]),
                "facing_changed": bool(sample["facing_changed"]),
                "projectile": bool(sample["projectile"]),
                "hitboxes": _frame_hitboxes(sample),
            }
        )

    for frame_number in frames[1:]:
        frame = frame_data.framedata[character][action][frame_number]
        signature = _frame_signature(character, action, frame_number, frame, frame_data)
        if signature != previous_signature:
            flush(frame_number - 1)
            segment_start = frame_number
            previous_signature = signature
    flush(frames[-1])
    return states


def get_framedata(character_query: str | int, action_query: str | int) -> dict[str, object]:
    character = resolve_character(character_query)
    actions = resolve_actions(character, action_query)
    frame_data = _frame_data()

    states: list[dict[str, object]] = []
    for entry in actions:
        states.extend(_states_for_action(character, entry))

    summary_actions: list[dict[str, object]] = []
    for entry in actions:
        summary_actions.append(
            {
                "action_id": entry.action_id,
                "action_enum": entry.action_enum,
                "action_label": entry.action_label,
                "action_state": entry.action_state,
                "total_frames": frame_data.frame_count(character, entry.action),
                "first_hitbox_frame": frame_data.first_hitbox_frame(character, entry.action),
                "last_hitbox_frame": frame_data.last_hitbox_frame(character, entry.action),
                "iasa_frame": frame_data.iasa(character, entry.action),
            }
        )

    section_name = character_section_name(character)
    return {
        "character": character.name,
        "character_id": int(character.value),
        "character_section": section_name,
        "action_query": str(action_query),
        "resolved_actions": summary_actions,
        "tags": _collect_tags(character, actions),
        "states": states,
    }


def _attack_state_matches(
    character: Character,
    action: Action,
    frame_number: int,
    attack_state_query: str | None,
) -> bool:
    if attack_state_query is None:
        return True
    normalized = _normalize_token(attack_state_query)
    attack = _frame_data().attack_state(character, action, frame_number)
    return _normalize_token(attack.name) == normalized


def _action_state_matches(entry: ResolvedAction, action_state_query: str | None) -> bool:
    if action_state_query is None:
        return True
    normalized = _normalize_token(action_state_query)
    candidates = {
        _normalize_token(entry.action_state or ""),
        _normalize_token(entry.action_enum),
        str(entry.action_id),
    }
    return normalized in candidates or any(
        normalized in candidate for candidate in candidates if candidate
    )


def get_raw_framedata_csv(
    character_query: str | int,
    action_query: str | int,
    *,
    action_state: str | None = None,
    attack_state: str | None = None,
    frame_start: int | None = None,
    frame_end: int | None = None,
    max_rows: int = _MAX_CSV_ROWS,
) -> dict[str, object]:
    if max_rows < 1:
        msg = "max_rows must be at least 1"
        raise FramedataQueryError(msg)
    if max_rows > _MAX_CSV_ROWS:
        msg = f"max_rows cannot exceed {_MAX_CSV_ROWS}"
        raise FramedataQueryError(msg)

    character = resolve_character(character_query)
    actions = resolve_actions(character, action_query)
    if action_state is not None:
        actions = [entry for entry in actions if _action_state_matches(entry, action_state)]
        if not actions:
            msg = f"no actions matched action_state filter {action_state!r}"
            raise FramedataQueryError(msg)

    character_id = int(character.value)
    action_ids = {entry.action_id for entry in actions}
    rows: list[dict[str, str]] = []
    truncated = False

    with _open_framedata_csv() as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if int(row["character"]) != character_id:
                continue
            action_id = int(row["action"])
            if action_id not in action_ids:
                continue
            frame_number = int(row["frame"])
            if frame_start is not None and frame_number < frame_start:
                continue
            if frame_end is not None and frame_number > frame_end:
                continue
            action = Action(action_id)
            if not _attack_state_matches(character, action, frame_number, attack_state):
                continue
            rows.append(dict(row))
            if len(rows) >= max_rows:
                truncated = True
                break

    return {
        "character": character.name,
        "character_id": character_id,
        "action_query": str(action_query),
        "filters": {
            "action_state": action_state,
            "attack_state": attack_state,
            "frame_start": frame_start,
            "frame_end": frame_end,
            "max_rows": max_rows,
        },
        "resolved_action_ids": sorted(action_ids),
        "truncated": truncated,
        "row_count": len(rows),
        "rows": rows,
    }
