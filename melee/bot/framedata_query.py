"""Query libmelee framedata for bot-author agents and tooling.

This module exposes two query entry points:

* :func:`get_framedata` returns synthetic, fully-typed framedata for a
  character/action query — a :class:`FramedataResult` containing one
  :class:`ActionSummary` per resolved action plus an ordered list of
  :class:`FrameSegment` snapshots. Segments are explicit, significant state
  transitions in the framedata: a new segment begins whenever any tracked
  property of a frame changes — a hitbox appearing or disappearing, a hitbox
  stat (size, x, y) changing, the attack phase (windup/attacking/cooldown)
  advancing, the IASA flag flipping, locomotion shifting, the facing flag
  toggling, or a projectile spawning. Each segment is inclusive on both ends
  (it covers ``[start_frame, end_frame]``).

* :func:`get_raw_framedata_csv` streams the raw framedata CSV filtered by
  character/action/frame range. Returns a :class:`RawFramedataCsvResult`.

Note:
    The framedata CSV does not carry per-frame invulnerability (iframe)
    information. Melee iframes are determined by the action enum, not by
    framedata rows, so :attr:`ActionSummary.has_invulnerability` is the best
    signal available here: it is ``True`` for actions libmelee classifies as
    rolls/dodges/techs/getups via :meth:`FrameData.is_roll`. For exact iframe
    windows use the action's segment boundaries (most invulnerable-state
    transitions also flip a tracked property) plus ``PlayerState.invulnerable``
    on a live game state.

Caching:
    Per ``(character, action)`` the segment list and action summary are
    constructed once and cached via :func:`functools.lru_cache`.
    ``get_framedata`` itself assembles cached pieces cheaply; repeated queries
    for the same character/action pair do not re-walk the framedata.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final, TextIO, TypedDict

import melee
from melee.bot.action_names import (
    action_name,
    action_state_ident,
    character_section_name,
)
from melee.enums import Action, AttackState, Character
from melee.framedata import FrameData

_MAX_CSV_ROWS: Final[int] = 200
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
# DESNOTE(jbarber, 2026-08-21): Formatted labels cannot identify special slots:
# blocks vary by fighter, Peach orders down-B before neutral-B, Kirby has copy
# move IDs, and some special-looking Samus states are tagged Default. These IDs
# follow each doldecomp MotionState table's FtMoveId field at commit 68f92c47;
# resolution still filters actions absent from libmelee's enum or framedata.csv.
# See https://github.com/doldecomp/melee/tree/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara
_SPECIAL_SLOT_ACTION_IDS: Final[dict[Character, dict[str, tuple[int, ...]]]] = {
    Character.MARIO: {
        "neutral-special": (343, 344),
        "side-special": (345, 346),
        "up-special": (347, 348),
        "down-special": (349, 350),
    },
    Character.FOX: {
        "neutral-special": tuple(range(341, 347)),
        "side-special": tuple(range(347, 353)),
        "up-special": tuple(range(353, 360)),
        "down-special": tuple(range(360, 370)),
    },
    Character.CPTFALCON: {
        "neutral-special": tuple(range(347, 349)),
        "side-special": tuple(range(349, 353)),
        "up-special": tuple(range(353, 357)),
        "down-special": tuple(range(357, 364)),
    },
    Character.DK: {
        "neutral-special": tuple(range(369, 379)),
        "side-special": (379, 380),
        "up-special": (381, 382),
        "down-special": tuple(range(383, 387)),
    },
    Character.KIRBY: {
        "neutral-special": tuple(range(353, 383)) + tuple(range(399, 544)),
        "side-special": (383, 384),
        "up-special": tuple(range(385, 393)),
        "down-special": tuple(range(393, 399)),
    },
    Character.BOWSER: {
        "neutral-special": tuple(range(341, 347)),
        "side-special": tuple(range(347, 359)),
        "up-special": (359, 360),
        "down-special": (361, 362, 363),
    },
    Character.LINK: {
        "neutral-special": tuple(range(344, 350)),
        "side-special": tuple(range(350, 356)),
        "up-special": (356, 357),
        "down-special": (358, 359),
    },
    Character.SHEIK: {
        "neutral-special": tuple(range(341, 349)),
        "side-special": tuple(range(349, 355)),
        "up-special": tuple(range(355, 361)),
        "down-special": tuple(range(361, 365)),
    },
    Character.NESS: {
        "neutral-special": tuple(range(348, 356)),
        "side-special": (356, 357),
        "up-special": tuple(range(358, 367)),
        "down-special": tuple(range(367, 377)),
    },
    Character.PEACH: {
        "neutral-special": tuple(range(365, 369)),
        "side-special": tuple(range(354, 361)),
        "up-special": tuple(range(361, 365)),
        "down-special": (352, 353),
    },
    Character.POPO: {
        "neutral-special": (341, 342),
        "side-special": tuple(range(343, 347)) + (359, 360),
        "up-special": tuple(range(347, 357)) + tuple(range(361, 367)),
        "down-special": (357, 358),
    },
    Character.NANA: {
        "neutral-special": (341, 342),
        "side-special": tuple(range(343, 347)) + (359, 360),
        "up-special": tuple(range(347, 357)) + tuple(range(361, 367)),
        "down-special": (357, 358),
    },
    Character.PIKACHU: {
        "neutral-special": (341, 342),
        "side-special": tuple(range(343, 353)),
        "up-special": tuple(range(353, 359)),
        "down-special": tuple(range(359, 367)),
    },
    Character.SAMUS: {
        "neutral-special": tuple(range(343, 349)),
        "side-special": tuple(range(349, 353)),
        "up-special": (353, 354),
        "down-special": (355, 356),
    },
    Character.YOSHI: {
        "neutral-special": tuple(range(346, 356)),
        "side-special": tuple(range(356, 364)),
        "up-special": (364, 365),
        "down-special": (366, 367, 368),
    },
    Character.JIGGLYPUFF: {
        "neutral-special": tuple(range(346, 363)),
        "side-special": (363, 364),
        "up-special": tuple(range(365, 369)),
        "down-special": tuple(range(369, 373)),
    },
    Character.MEWTWO: {
        "neutral-special": tuple(range(341, 351)),
        "side-special": (351, 352),
        "up-special": tuple(range(353, 359)),
        "down-special": (359, 360),
    },
    Character.LUIGI: {
        "neutral-special": (341, 342),
        "side-special": tuple(range(343, 355)),
        "up-special": (355, 356),
        "down-special": (357, 358),
    },
    Character.MARTH: {
        "neutral-special": tuple(range(341, 349)),
        "side-special": tuple(range(349, 367)),
        "up-special": (367, 368),
        "down-special": tuple(range(369, 373)),
    },
    Character.ZELDA: {
        "neutral-special": (341, 342),
        "side-special": tuple(range(343, 349)),
        "up-special": tuple(range(349, 355)),
        "down-special": tuple(range(355, 359)),
    },
    Character.YLINK: {
        "neutral-special": tuple(range(344, 350)),
        "side-special": tuple(range(350, 356)),
        "up-special": (356, 357),
        "down-special": (358, 359),
    },
    Character.DOC: {
        "neutral-special": (343, 344),
        "side-special": (345, 346),
        "up-special": (347, 348),
        "down-special": (349, 350),
    },
    Character.FALCO: {
        "neutral-special": tuple(range(341, 347)),
        "side-special": tuple(range(347, 353)),
        "up-special": tuple(range(353, 360)),
        "down-special": tuple(range(360, 370)),
    },
    Character.PICHU: {
        "neutral-special": (341, 342),
        "side-special": tuple(range(343, 353)),
        "up-special": tuple(range(353, 359)),
        "down-special": tuple(range(359, 367)),
    },
    Character.GAMEANDWATCH: {
        "neutral-special": (353, 354),
        "side-special": tuple(range(355, 373)),
        "up-special": (373, 374),
        "down-special": tuple(range(375, 381)),
    },
    Character.GANONDORF: {
        "neutral-special": tuple(range(347, 349)),
        "side-special": tuple(range(349, 353)),
        "up-special": tuple(range(353, 357)),
        "down-special": tuple(range(357, 364)),
    },
    Character.ROY: {
        "neutral-special": tuple(range(341, 349)),
        "side-special": tuple(range(349, 367)),
        "up-special": (367, 368),
        "down-special": tuple(range(369, 373)),
    },
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


@dataclass(frozen=True)
class HitboxSnapshot:
    """One hitbox's status within a frame segment.

    Hereditary across all frames in the segment — segments only exist while
    every hitbox's (active, size, x, y) tuple is stable, so the values on the
    segment's first frame are representative of the whole span.
    """

    index: int
    """Hitbox slot (1-4)."""

    active: bool
    """Whether this hitbox is currently producing a hitbox (``hitbox_N_status``)."""

    size: float
    """Hitbox radius."""

    x: float
    """Hitbox center X relative to the character's root bone."""

    y: float
    """Hitbox center Y relative to the character's root bone."""

    min_x: float
    """Leftmost extent of the hitbox (``x - size``)."""

    max_x: float
    """Rightmost extent of the hitbox (``x + size``)."""

    min_y: float
    """Lowermost extent of the hitbox (``y - size``)."""

    max_y: float
    """Uppermost extent of the hitbox (``y + size``)."""


@dataclass(frozen=True)
class FrameSegment:
    """A contiguous run of frames sharing an identical framedata signature.

    Segments are explicit, significant state transitions in framedata. A new
    segment begins whenever any tracked framedata property changes between
    adjacent frames:

    * any hitbox's ``status``, ``size``, ``x``, or ``y`` changes
      (a hitbox appears, disappears, or shifts)
    * the attack phase advances (WINDUP/ATTACKING/COOLDOWN/NOT_ATTACKING)
    * the IASA flag flips
    * the ``locomotion_x``/``locomotion_y`` delta changes (rounded to 4 dp)
    * the ``facing_changed`` flag toggles
    * the ``projectile`` flag toggles

    Both ``start_frame`` and ``end_frame`` are inclusive, and
    ``frame_count == end_frame - start_frame + 1``.
    """

    start_frame: int
    end_frame: int
    frame_count: int
    attack_state: AttackState
    locomotion_x: float
    locomotion_y: float
    iasa: bool
    facing_changed: bool
    projectile: bool
    hitboxes: tuple[HitboxSnapshot, ...]
    """Fixed-length 4-tuple sampled from ``start_frame``."""


@dataclass(frozen=True)
class HitboxActiveRange:
    """A contiguous range of frames where a specific hitbox is active.

    Used to answer "when does hitbox N come out, and when does it go away?"
    for a given action. A single action can yield multiple ranges per hitbox
    index when the hitbox pulses on and off (e.g. Marth's side-B dance).
    """

    hitbox_index: int
    """Hitbox slot (1-4)."""

    start_frame: int
    """First frame the hitbox is active (inclusive)."""

    end_frame: int
    """Last frame the hitbox is active (inclusive)."""

    frame_count: int
    """Number of frames the hitbox is active (``end_frame - start_frame + 1``)."""


@dataclass(frozen=True)
class ActionSummary:
    """High-level framedata summary for a single resolved action.

    Surfaces the questions bot authors most commonly ask of an action:

    * ``first_hitbox_frame`` — how many frames until the attack is out
      (``-1`` if the action has no hitboxes).
    * ``hitbox_active_ranges`` — when each hitbox is active vs. inactive.
    * ``iasa_frame`` — first IASA (interruptible-as-of) frame, ``-1`` if none.
    * ``last_hitbox_frame`` — last frame any hitbox is active, ``-1`` if none.
    * ``has_invulnerability`` — whether this action is classified as a
      roll/dodge/tech/getup by :meth:`FrameData.is_roll` (per the framedata
      CSV limitation, this does not carry exact per-frame iframe windows).
    """

    action_id: int
    action_enum: str
    action_label: str
    action_state: str | None
    total_frames: int
    first_hitbox_frame: int
    last_hitbox_frame: int
    iasa_frame: int
    has_invulnerability: bool
    hitbox_active_ranges: tuple[HitboxActiveRange, ...]


@dataclass(frozen=True)
class FramedataResult:
    """Fully-typed result of :func:`get_framedata`.

    Combines resolved-action summaries with the segment-by-segment state
    transitions across all matched actions. ``segments`` is the concatenation
    of every resolved action's segments in action-id order.
    """

    character: str
    character_id: int
    character_section: str | None
    action_query: str
    resolved_actions: tuple[ActionSummary, ...]
    tags: tuple[str, ...]
    segments: tuple[FrameSegment, ...]


class RawFramedataRow(TypedDict):
    """One row of the framedata CSV (all values are unparsed strings)."""

    character: str
    action: str
    frame: str
    hitbox_1_status: str
    hitbox_1_size: str
    hitbox_1_x: str
    hitbox_1_y: str
    hitbox_2_status: str
    hitbox_2_size: str
    hitbox_2_x: str
    hitbox_2_y: str
    hitbox_3_status: str
    hitbox_3_size: str
    hitbox_3_x: str
    hitbox_3_y: str
    hitbox_4_status: str
    hitbox_4_size: str
    hitbox_4_x: str
    hitbox_4_y: str
    locomotion_x: str
    locomotion_y: str
    iasa: str
    facing_changed: str
    projectile: str


@dataclass(frozen=True)
class RawFramedataCsvFilters:
    """Echo of the filters applied to a :func:`get_raw_framedata_csv` query."""

    action_state: str | None
    attack_state: str | None
    frame_start: int | None
    frame_end: int | None
    max_rows: int


@dataclass(frozen=True)
class RawFramedataCsvResult:
    """Fully-typed result of :func:`get_raw_framedata_csv`."""

    character: str
    character_id: int
    action_query: str
    filters: RawFramedataCsvFilters
    resolved_action_ids: tuple[int, ...]
    truncated: bool
    row_count: int
    rows: tuple[RawFramedataRow, ...]


@lru_cache(maxsize=1)
def _frame_data() -> FrameData:
    """Return the process-wide :class:`FrameData` singleton.

    Built once per process (``lru_cache(maxsize=1)``); shared by all framedata
    query helpers so the CSV is parsed at most once.
    """
    return FrameData()


def _open_framedata_csv() -> TextIO:
    """Open ``framedata.csv`` for reading.

    Resolves the file shipped inside the installed ``melee`` package, or the
    legacy vendored fallback at ``vendor/libmelee/melee/framedata.csv``.
    Raises :class:`FramedataQueryError` if neither exists.
    """
    package_csv = Path(melee.__file__).resolve().parent / "framedata.csv"
    if package_csv.is_file():
        return package_csv.open(newline="")
    legacy = Path(__file__).resolve().parents[2] / "vendor/libmelee/melee/framedata.csv"
    if legacy.is_file():
        return legacy.open(newline="")
    msg = "framedata.csv is missing from the installed melee package"
    raise FramedataQueryError(msg)


def _normalize_token(value: str) -> str:
    """Lowercase ``value`` and strip all non-alphanumeric characters."""
    return _NORMALIZE_RE.sub("", value.strip().lower())


def resolve_character(character: str | int) -> Character:
    """Resolve a character slug, enum name, or numeric ID to a :class:`Character`.

    Accepts slugs (``"fox"``, ``"captain_falcon"``), enum names
    (``"FOX"``, ``"JIGGLYPUFF"``), or numeric IDs (``1``). Raises
    :class:`FramedataQueryError` when the character is unknown.

    Args:
        character: Slug, enum name, or numeric ID of the character.
    """
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


def _resolve_action_entry(character: Character, action: Action) -> ResolvedAction:
    """Build a :class:`ResolvedAction` from an ``(character, action)`` pair."""
    action_id = int(action.value)
    return ResolvedAction(
        action=action,
        action_id=action_id,
        action_enum=action.name,
        action_label=action_name(character, action),
        action_state=action_state_ident(character, action_id),
    )


def _resolve_special_slot(character: Character, slot: str) -> list[ResolvedAction]:
    """Return the sub-actions for one of ``character``'s special-move slots.

    ``slot`` may be ``"neutral-special"``, ``"side-special"``,
    ``"up-special"``, or ``"down-special"`` (case/whitespace insensitive; the
    common ``"side-b"`` etc. aliases are also accepted). Raises
    :class:`FramedataQueryError` for unknown slots or slots the character lacks.
    """
    normalized = _SPECIAL_SLOT_BY_NORMALIZED.get(_normalize_token(slot))
    if normalized is None:
        msg = f"unknown special slot: {slot!r}"
        raise FramedataQueryError(msg)
    special_action_ids = _SPECIAL_SLOT_ACTION_IDS.get(character, {}).get(normalized)
    if special_action_ids is None:
        msg = f"no {normalized!r} motion-state mapping for {character.name}"
        raise FramedataQueryError(msg)

    available_actions = _frame_data().framedata.get(character)
    if available_actions is None:
        msg = f"no framedata for {character.name}"
        raise FramedataQueryError(msg)

    actions: list[ResolvedAction] = []
    for action_id in special_action_ids:
        try:
            action = Action(action_id)
        except ValueError:
            continue
        if action in available_actions:
            actions.append(_resolve_action_entry(character, action))
    if not actions:
        msg = f"no framedata for {character.name} {normalized!r}"
        raise FramedataQueryError(msg)
    return actions


def _match_actions_by_label(character: Character, query: str) -> list[ResolvedAction]:
    """Fuzzy-match ``query`` against action labels / enum names / state idents.

    Tries exact normalized matches first, falling back to substring matches.
    Returns matches sorted by ``action_id``, or an empty list when none match.
    """
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
    """Resolve ``action_query`` to one or more :class:`ResolvedAction` entries.

    Accepts:
      * an integer action ID,
      * a special-slot alias (``"side-special"``, ``"up-b"``, …),
      * the enum name of an :class:`Action`,
      * a fuzzy match on the human-readable move label, the enum name, or
        the action-state identifier from :func:`action_state_ident`.

    Raises :class:`FramedataQueryError` when the action is unknown or the
    character has no framedata for a resolved enum name.

    Args:
        character: Already-resolved :class:`Character`.
        action_query: Slug, enum name, numeric ID, or special-slot alias.
    """
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


def _hitbox_snapshot(index: int, status: bool, size: float, x: float, y: float) -> HitboxSnapshot:
    """Construct a :class:`HitboxSnapshot` and its derived bounding box."""
    return HitboxSnapshot(
        index=index,
        active=status,
        size=size,
        x=x,
        y=y,
        min_x=x - size,
        max_x=x + size,
        min_y=y - size,
        max_y=y + size,
    )


def _frame_hitboxes(frame: FramedataFrame) -> tuple[HitboxSnapshot, ...]:
    """Return fixed-length 4-tuple of hitbox snapshots for one framedata frame."""
    return (
        _hitbox_snapshot(
            1,
            frame["hitbox_1_status"],
            frame["hitbox_1_size"],
            frame["hitbox_1_x"],
            frame["hitbox_1_y"],
        ),
        _hitbox_snapshot(
            2,
            frame["hitbox_2_status"],
            frame["hitbox_2_size"],
            frame["hitbox_2_x"],
            frame["hitbox_2_y"],
        ),
        _hitbox_snapshot(
            3,
            frame["hitbox_3_status"],
            frame["hitbox_3_size"],
            frame["hitbox_3_x"],
            frame["hitbox_3_y"],
        ),
        _hitbox_snapshot(
            4,
            frame["hitbox_4_status"],
            frame["hitbox_4_size"],
            frame["hitbox_4_x"],
            frame["hitbox_4_y"],
        ),
    )


def _frame_signature(
    character: Character,
    action: Action,
    frame_number: int,
    frame: FramedataFrame,
    frame_data: FrameData,
) -> tuple[object, ...]:
    """Return the tuple compared to detect frame-to-frame state transitions.

    Two adjacent frames with the same signature belong to the same
    :class:`FrameSegment`; a change opens a new segment.
    """
    attack = frame_data.attack_state(character, action, frame_number)
    hitboxes = tuple(
        (box.active, box.size, box.x, box.y) for box in _frame_hitboxes(frame)
    )
    return (
        action_state_ident(character, int(action.value)),
        attack,
        round(float(frame["locomotion_x"]), 4),
        round(float(frame["locomotion_y"]), 4),
        hitboxes,
        bool(frame["iasa"]),
        bool(frame["facing_changed"]),
        bool(frame["projectile"]),
    )


def _collect_tags(character: Character, actions: Sequence[ResolvedAction]) -> list[str]:
    """Build a sorted tag set summarizing the resolved actions.

    Tags include ``GRAB``, ``B_MOVE``, ``ATTACK``, ``ROLL``, ``SHIELD``,
    ``IASA``, and ``PROJECTILE``. Useful for quick archetype classification of
    a query's resolved sub-actions (e.g. a side-B that is also a grab).
    """
    frame_data = _frame_data()
    tags: set[str] = set()
    for entry in actions:
        action = entry.action
        if frame_data.is_grab(character, action):
            tags.add("GRAB")
        if frame_data.is_bmove(character, action):
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


@lru_cache(maxsize=None)
def _action_segments(character: Character, action: Action) -> tuple[FrameSegment, ...]:
    """Return the ordered list of significant state transitions for one action.

    Cached per (character, action); constructed exactly once and reused across
    repeated queries. Each segment captures a maximal run of frames whose
    framedata signature (hitbox status/size/position, attack phase, locomotion,
    IASA, facing, projectile flags) is unchanged.
    """
    frame_data = _frame_data()
    frames = sorted(frame_data.framedata[character][action])
    if not frames:
        return ()

    segments: list[FrameSegment] = []
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
        segments.append(
            FrameSegment(
                start_frame=segment_start,
                end_frame=end_frame,
                frame_count=end_frame - segment_start + 1,
                attack_state=attack,
                locomotion_x=float(sample["locomotion_x"]),
                locomotion_y=float(sample["locomotion_y"]),
                iasa=bool(sample["iasa"]),
                facing_changed=bool(sample["facing_changed"]),
                projectile=bool(sample["projectile"]),
                hitboxes=_frame_hitboxes(sample),
            )
        )

    for frame_number in frames[1:]:
        frame = frame_data.framedata[character][action][frame_number]
        signature = _frame_signature(character, action, frame_number, frame, frame_data)
        if signature != previous_signature:
            flush(frame_number - 1)
            segment_start = frame_number
            previous_signature = signature
    flush(frames[-1])
    return tuple(segments)


def _hitbox_active_ranges(
    character: Character,
    action: Action,
) -> tuple[HitboxActiveRange, ...]:
    """Return per-hitbox contiguous active ranges for one action.

    Walks framedata frames in order, splitting on transitions between
    inactive/active for each of the four hitbox slots. A single hitbox that
    pulses on, off, and on again yields two ranges.
    """
    frame_data = _frame_data()
    frames = sorted(frame_data.framedata[character][action])
    if not frames:
        return ()
    statuses: dict[int, list[tuple[int, bool]]] = {i: [] for i in (1, 2, 3, 4)}
    for frame_number in frames:
        frame = frame_data.framedata[character][action][frame_number]
        statuses[1].append((frame_number, bool(frame["hitbox_1_status"])))
        statuses[2].append((frame_number, bool(frame["hitbox_2_status"])))
        statuses[3].append((frame_number, bool(frame["hitbox_3_status"])))
        statuses[4].append((frame_number, bool(frame["hitbox_4_status"])))

    ranges: list[HitboxActiveRange] = []
    for index in (1, 2, 3, 4):
        run_start: int | None = None
        prev_active = False
        for frame_number, active in statuses[index]:
            if active and not prev_active:
                run_start = frame_number
            elif not active and prev_active and run_start is not None:
                ranges.append(
                    HitboxActiveRange(
                        hitbox_index=index,
                        start_frame=run_start,
                        end_frame=frame_number - 1,
                        frame_count=frame_number - run_start,
                    )
                )
                run_start = None
            prev_active = active
        if run_start is not None:
            last_frame = statuses[index][-1][0]
            ranges.append(
                HitboxActiveRange(
                    hitbox_index=index,
                    start_frame=run_start,
                    end_frame=last_frame,
                    frame_count=last_frame - run_start + 1,
                )
            )
    return tuple(ranges)


@lru_cache(maxsize=None)
def _action_summary(character: Character, action: Action) -> ActionSummary:
    """Return the :class:`ActionSummary` for one action, cached per (char, action)."""
    frame_data = _frame_data()
    entry = _resolve_action_entry(character, action)
    return ActionSummary(
        action_id=entry.action_id,
        action_enum=entry.action_enum,
        action_label=entry.action_label,
        action_state=entry.action_state,
        total_frames=frame_data.frame_count(character, action),
        first_hitbox_frame=frame_data.first_hitbox_frame(character, action),
        last_hitbox_frame=frame_data.last_hitbox_frame(character, action),
        iasa_frame=frame_data.iasa(character, action),
        has_invulnerability=frame_data.is_roll(character, action),
        hitbox_active_ranges=_hitbox_active_ranges(character, action),
    )


@lru_cache(maxsize=None)
def get_framedata(
    character_query: str | int,
    action_query: str | int,
) -> FramedataResult:
    """Return typed framedata for a character/action query.

    The result's :attr:`FramedataResult.segments` capture every significant
    framedata state transition across all resolved actions — a new segment
    opens whenever any tracked framedata property changes (a hitbox appears,
    disappears, or shifts; the attack phase advances; the IASA flag flips;
    locomotion/facing/projectile flags change). Per-action
    :class:`ActionSummary` entries surface hitbox timing windows
    (:attr:`ActionSummary.hitbox_active_ranges`), IASA frame, and
    invulnerability classification.

    Args:
        character_query: Character slug, enum name, or numeric ID
            (e.g. ``"fox"``, ``"FOX"``, ``1``).
        action_query: Action slug, enum name, numeric ID, or special-slot
            alias (e.g. ``"side-special"``, ``"Illusion"``, ``347``).

    Returns:
        A fully-type :class:`FramedataResult` with ``segments`` ordered by
        ``start_frame`` per resolved action, and ``resolved_actions`` ordered
        by ``action_id``.

    Note:
        Memoized by ``(character_query, action_query)``. Repeated calls with
        the same arguments return the same :class:`FramedataResult` instance
        (and therefore the same segment/summary tuples). Per-``(Character,
        Action)`` building blocks are also cached separately, so even queries
        with different string aliases for the same character/action share the
        expensive framedata walk.

    Example:
        A bot-author agent wants "how many frames until Fox's side-B is
        active, and how long does the hitbox last?"::

            result = get_framedata("fox", "side-special")
            for action in result.resolved_actions:
                if action.first_hitbox_frame < 0:
                    continue
                print(action.action_label,
                      "first hitbox:", action.first_hitbox_frame,
                      "active ranges:", [
                          (r.start_frame, r.end_frame)
                          for r in action.hitbox_active_ranges
                          if r.hitbox_index == 1
                      ])
    """
    character = resolve_character(character_query)
    actions = resolve_actions(character, action_query)

    segments: list[FrameSegment] = []
    summaries: list[ActionSummary] = []
    for entry in actions:
        segments.extend(_action_segments(character, entry.action))
        summaries.append(_action_summary(character, entry.action))

    return FramedataResult(
        character=character.name,
        character_id=int(character.value),
        character_section=character_section_name(character),
        action_query=str(action_query),
        resolved_actions=tuple(summaries),
        tags=tuple(_collect_tags(character, actions)),
        segments=tuple(segments),
    )


def _attack_state_matches(
    character: Character,
    action: Action,
    frame_number: int,
    attack_state_query: str | None,
) -> bool:
    """Return whether one frame's attack state matches a query string.

    ``attack_state_query`` is matched against :meth:`FrameData.attack_state`
    names (``WINDUP``, ``ATTACKING``, ``COOLDOWN``, ``NOT_ATTACKING``). When
    ``attack_state_query is None`` the filter is suppressed.
    """
    if attack_state_query is None:
        return True
    normalized = _normalize_token(attack_state_query)
    attack = _frame_data().attack_state(character, action, frame_number)
    return _normalize_token(attack.name) == normalized


def _action_state_matches(entry: ResolvedAction, action_state_query: str | None) -> bool:
    """Return whether an action matches an action-state / enum / id filter.

    ``action_state_query`` is matched against the resolved action-state ident,
    the enum name, the numeric ID, or any substring of those. When
    ``action_state_query is None`` the filter is suppressed.
    """
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
) -> RawFramedataCsvResult:
    """Return raw framedata CSV rows for a character/action query as typed data.

    All row values are unparsed strings (the CSV is consumed as-text). Use
    :func:`get_framedata` for parsed, segmented framedata — i.e. when you want
    explicit transitions like "new hitbox appeared" / "hitbox disappeared" /
    "hitbox stat changed" rather than raw per-frame rows.

    Args:
        character_query: Character slug, enum name, or numeric ID.
        action_query: Action slug, enum name, numeric ID, or special-slot alias.
        action_state: Optional fuzzy filter on action-state / enum / id.
        attack_state: Optional filter on ``AttackState`` name
            (``windup``/``attacking``/``cooldown``/``not_attacking``).
        frame_start: First frame to include (inclusive); ``None`` = unbounded.
        frame_end: Last frame to include (inclusive); ``None`` = unbounded.
        max_rows: Hard cap on returned rows. Defaults to :data:`_MAX_CSV_ROWS`
            (200); must be in ``[1, _MAX_CSV_ROWS]``.

    Raises:
        FramedataQueryError: On invalid ``max_rows``, unknown character/action,
            or an ``action_state`` filter that matches nothing.
    """
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
    rows: list[RawFramedataRow] = []
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
            rows.append(row)  # type: ignore[arg-type]
            if len(rows) >= max_rows:
                truncated = True
                break

    return RawFramedataCsvResult(
        character=character.name,
        character_id=character_id,
        action_query=str(action_query),
        filters=RawFramedataCsvFilters(
            action_state=action_state,
            attack_state=attack_state,
            frame_start=frame_start,
            frame_end=frame_end,
            max_rows=max_rows,
        ),
        resolved_action_ids=tuple(sorted(action_ids)),
        truncated=truncated,
        row_count=len(rows),
        rows=tuple(rows),
    )
