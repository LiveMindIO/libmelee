"""Query libmelee framedata for bot-author agents and tooling.

This module exposes two query entry points:

* :func:`get_framedata` returns source-derived, fully-typed framedata for a
  character/action query — a :class:`FramedataResult` containing one
  :class:`ActionSummary` per resolved action plus an ordered list of
  :class:`FrameSegment` snapshots. Segments are explicit, significant state
  transitions in the framedata: a new segment begins whenever any tracked
  property of a frame changes — a hitbox appearing or disappearing, a hitbox
  stat (size, x, y) changing, the attack phase (windup/attacking/cooldown)
  advancing, the IASA flag flipping, or an available source-specific property
  changing. Historical CSV results include locomotion, facing, projectile, and
  runtime-captured XY geometry. ISO results leave those fields ``None`` while
  retaining script-proven hitbox activity, size, and timing. Each segment is
  inclusive on both ends (it covers ``[start_frame, end_frame]``).

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
    Results and their building blocks are cached by resolved source path as well
    as character/action. Changing ``MELEE_ISO_PATH`` selects a different cache
    entry. Call :func:`clear_framedata_query_caches` after replacing an ISO at
    the same path.
"""

from __future__ import annotations

import csv
import os
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import cache, lru_cache
from itertools import groupby
from pathlib import Path
from typing import Final, Literal, Protocol, TextIO, TypedDict, cast

import melee
from melee.bot.action_names import (
    action_name,
    action_state_ident,
    character_section_name,
)
from melee.disc_framedata import DiscBuild, FrameSnapshot
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
        "side-special": (*range(343, 347), 359, 360),
        "up-special": (*range(347, 357), *range(361, 367)),
        "down-special": (357, 358),
    },
    Character.NANA: {
        "neutral-special": (341, 342),
        "side-special": (*range(343, 347), 359, 360),
        "up-special": (*range(347, 357), *range(361, 367)),
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

    x: float | None
    """Runtime-captured root-relative X, or ``None`` for ISO results."""

    y: float | None
    """Runtime-captured root-relative Y, or ``None`` for ISO results."""

    min_x: float | None
    """Leftmost extent of the hitbox (``x - size``)."""

    max_x: float | None
    """Rightmost extent of the hitbox (``x + size``)."""

    min_y: float | None
    """Lowermost extent of the hitbox (``y - size``)."""

    max_y: float | None
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
    * the ``locomotion_x``/``locomotion_y`` delta changes when available
    * the ``facing_changed`` flag toggles when available
    * the ``projectile`` flag toggles when available

    Both ``start_frame`` and ``end_frame`` are inclusive, and
    ``frame_count == end_frame - start_frame + 1``.
    """

    start_frame: int
    end_frame: int
    frame_count: int
    attack_state: AttackState
    locomotion_x: float | None
    locomotion_y: float | None
    iasa: bool
    facing_changed: bool | None
    projectile: bool | None
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
class FramedataSource:
    """Provenance for one high-level framedata result."""

    kind: Literal["csv", "iso"]
    """Selected source kind."""

    disc_build: DiscBuild | None = None
    """Validated disc identity for ISO results; otherwise ``None``."""


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
    source: FramedataSource = FramedataSource("csv")
    """Source kind and optional validated disc-build provenance."""


class _CacheInfo(Protocol):
    @property
    def maxsize(self) -> int | None: ...


class _CachedFramedataQuery(Protocol):
    """Callable shape retained from the former ``@lru_cache`` wrapper."""

    def __call__(self, character_query: str | int, action_query: str | int) -> FramedataResult: ...

    cache_clear: Callable[[], None]
    cache_info: Callable[[], _CacheInfo]
    cache_parameters: Callable[[], object]


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


def _configured_iso_path() -> Path | None:
    """Return the configured ISO path used as the query-cache source key."""

    value = os.environ.get("MELEE_ISO_PATH")
    return Path(value).expanduser().resolve() if value else None


@lru_cache(maxsize=4)
def _frame_data(iso_path: Path | None = None) -> FrameData:
    """Return a process-wide helper for one explicit framedata source."""

    return FrameData(
        iso_path=iso_path,
        use_iso_environment=False,
        _warn_deprecated=False,
    )


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


@lru_cache(maxsize=128)
def _available_actions(iso_path: Path | None, character: Character) -> tuple[Action, ...]:
    """Return queryable actions from the selected source."""

    frame_data = _frame_data(iso_path)
    if iso_path is None:
        return tuple(frame_data.framedata[character])
    disc = frame_data._disc_framedata
    assert disc is not None
    return tuple(
        action
        for action in Action
        if (record := disc.action_for_state(character, action)) is not None and record.timeline.frames
    )


def _special_slot_for_move_id(move_id: int) -> str | None:
    """Map the executable's ``FtMoveId`` special range to an input slot."""

    if move_id == 18 or 22 <= move_id <= 47:
        return "neutral-special"
    return {19: "side-special", 20: "up-special", 21: "down-special"}.get(move_id)


def _resolve_special_slot(
    character: Character,
    slot: str,
    iso_path: Path | None,
) -> list[ResolvedAction]:
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
    actions: list[ResolvedAction] = []
    available_actions = _available_actions(iso_path, character)
    if iso_path is None:
        special_action_ids = _SPECIAL_SLOT_ACTION_IDS.get(character, {}).get(normalized)
        if special_action_ids is None:
            msg = f"no {normalized!r} motion-state mapping for {character.name}"
            raise FramedataQueryError(msg)
        available = set(available_actions)
        for action_id in special_action_ids:
            try:
                action = Action(action_id)
            except ValueError:
                continue
            if action in available:
                actions.append(_resolve_action_entry(character, action))
    else:
        frame_data = _frame_data(iso_path)
        disc = frame_data._disc_framedata
        assert disc is not None
        for action in available_actions:
            state = disc.motion_state(character, action)
            if state is None or _special_slot_for_move_id(state.move_id) != normalized:
                continue
            frame_data.is_attack(character, action)
            actions.append(_resolve_action_entry(character, action))
    if not actions:
        msg = f"no framedata for {character.name} {normalized!r}"
        raise FramedataQueryError(msg)
    return sorted(actions, key=lambda entry: entry.action_id)


def _match_actions_by_label(
    character: Character,
    query: str,
    iso_path: Path | None,
) -> list[ResolvedAction]:
    """Fuzzy-match ``query`` against action labels / enum names / state idents.

    Tries exact normalized matches first, falling back to substring matches.
    Returns matches sorted by ``action_id``, or an empty list when none match.
    """
    normalized = _normalize_token(query)
    matches: list[ResolvedAction] = []
    available_actions = _available_actions(iso_path, character)
    for action in available_actions:
        entry = _resolve_action_entry(character, action)
        candidates = {
            _normalize_token(entry.action_label),
            _normalize_token(entry.action_enum),
            _normalize_token(entry.action_state or ""),
        }
        if normalized in candidates:
            matches.append(entry)
    if not matches:
        for action in available_actions:
            entry = _resolve_action_entry(character, action)
            candidates = (
                _normalize_token(entry.action_label),
                _normalize_token(entry.action_enum),
                _normalize_token(entry.action_state or ""),
            )
            if any(normalized in candidate for candidate in candidates if candidate):
                matches.append(entry)
    return sorted(matches, key=lambda entry: entry.action_id)


def _resolve_actions(
    character: Character,
    action_query: str | int,
    iso_path: Path | None,
) -> list[ResolvedAction]:
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
    available_actions = _available_actions(iso_path, character)
    if isinstance(action_query, int):
        action = Action(action_query)
        if action not in available_actions:
            msg = f"no framedata for {character.name} action id {action_query}"
            raise FramedataQueryError(msg)
        return [_resolve_action_entry(character, action)]

    token = action_query.strip()
    if token.isdigit():
        return _resolve_actions(character, int(token), iso_path)

    normalized = _normalize_token(token)
    slot = _SPECIAL_SLOT_BY_NORMALIZED.get(normalized)
    if slot is not None:
        return _resolve_special_slot(character, slot, iso_path)

    try:
        enum_action = Action[token.upper()]
    except KeyError:
        enum_action = None
    else:
        if enum_action in available_actions:
            return [_resolve_action_entry(character, enum_action)]

    label_matches = _match_actions_by_label(character, token, iso_path)
    if label_matches:
        return label_matches

    msg = f"unknown action for {character.name}: {action_query!r}"
    raise FramedataQueryError(msg)


def resolve_actions(character: Character, action_query: str | int) -> list[ResolvedAction]:
    """Resolve actions against the currently configured high-level source."""

    return _resolve_actions(character, action_query, _configured_iso_path())


def _hitbox_snapshot(
    index: int,
    status: bool,
    size: float,
    x: float | None,
    y: float | None,
) -> HitboxSnapshot:
    """Construct a :class:`HitboxSnapshot` and its derived bounding box."""
    return HitboxSnapshot(
        index=index,
        active=status,
        size=size,
        x=x,
        y=y,
        min_x=None if x is None else x - size,
        max_x=None if x is None else x + size,
        min_y=None if y is None else y - size,
        max_y=None if y is None else y + size,
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


def _iso_frame_hitboxes(frame: FrameSnapshot | None) -> tuple[HitboxSnapshot, ...]:
    """Return script-proven hitbox slots without inventing runtime geometry."""

    active = {
        hitbox.hitbox_id: hitbox
        for hitbox in (() if frame is None else frame.active_hitboxes)
        if not hitbox.requires_thrown_hitbox_owner
    }
    return tuple(
        _hitbox_snapshot(
            index + 1,
            index in active,
            active[index].size if index in active else 0.0,
            None,
            None,
        )
        for index in range(4)
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


def _collect_tags(
    character: Character,
    actions: Sequence[ResolvedAction],
    iso_path: Path | None,
) -> list[str]:
    """Build a sorted tag set summarizing the resolved actions.

    Tags include ``GRAB``, ``B_MOVE``, ``ATTACK``, ``ROLL``, ``SHIELD``,
    ``IASA``, and ``PROJECTILE``. Useful for quick archetype classification of
    a query's resolved sub-actions (e.g. a side-B that is also a grab).
    """
    frame_data = _frame_data(iso_path)
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
        if iso_path is None:
            for _, frame in frame_data.framedata[character][action].items():
                if frame and frame["projectile"]:
                    tags.add("PROJECTILE")
                    break
    return sorted(tags)


@cache
def _action_segments(
    iso_path: Path | None,
    character: Character,
    action: Action,
) -> tuple[FrameSegment, ...]:
    """Return the ordered list of significant state transitions for one action.

    Cached per (character, action); constructed exactly once and reused across
    repeated queries. Each segment captures a maximal run of frames whose
    framedata signature (hitbox status/size/position, attack phase, locomotion,
    IASA, facing, projectile flags) is unchanged.
    """
    frame_data = _frame_data(iso_path)
    if iso_path is not None:
        record = frame_data._disc_action(character, action)
        if record is None:
            return ()
        normalized_frames: dict[int, FrameSnapshot] = {}
        hitbox_offset = frame_data._disc_hitbox_frame_offset(character, action)
        for frame in record.timeline.frames:
            normalized_frames[max(1, frame.local_frame + hitbox_offset)] = frame
        total_frames = frame_data.frame_count(character, action)
        iasa_frame = frame_data.iasa(character, action)
        states = []
        for frame_number in range(1, total_frames + 1):
            hitboxes = _iso_frame_hitboxes(normalized_frames.get(frame_number))
            states.append(
                (
                    frame_number,
                    frame_data.attack_state(character, action, frame_number),
                    iasa_frame != -1 and frame_number >= iasa_frame,
                    hitboxes,
                )
            )
        segments = []
        for _, grouped_states in groupby(states, key=lambda state: state[1:]):
            group = list(grouped_states)
            start_frame, attack_state, iasa, hitboxes = group[0]
            end_frame = group[-1][0]
            segments.append(
                FrameSegment(
                    start_frame=start_frame,
                    end_frame=end_frame,
                    frame_count=end_frame - start_frame + 1,
                    attack_state=attack_state,
                    locomotion_x=None,
                    locomotion_y=None,
                    iasa=iasa,
                    facing_changed=None,
                    projectile=None,
                    hitboxes=hitboxes,
                )
            )
        return tuple(segments)

    frames = sorted(frame_data.framedata[character][action])
    if not frames:
        return ()

    segments: list[FrameSegment] = []
    segment_start = frames[0]
    previous_signature = _frame_signature(
        character,
        action,
        segment_start,
        cast(FramedataFrame, frame_data.framedata[character][action][segment_start]),
        frame_data,
    )

    def flush(end_frame: int) -> None:
        sample = cast(FramedataFrame, frame_data.framedata[character][action][segment_start])
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
        frame = cast(FramedataFrame, frame_data.framedata[character][action][frame_number])
        signature = _frame_signature(character, action, frame_number, frame, frame_data)
        if signature != previous_signature:
            flush(frame_number - 1)
            segment_start = frame_number
            previous_signature = signature
    flush(frames[-1])
    return tuple(segments)


def _hitbox_active_ranges(
    iso_path: Path | None,
    character: Character,
    action: Action,
) -> tuple[HitboxActiveRange, ...]:
    """Return per-hitbox contiguous active ranges for one action.

    Walks framedata frames in order, splitting on transitions between
    inactive/active for each of the four hitbox slots. A single hitbox that
    pulses on, off, and on again yields two ranges.
    """
    ranges: list[HitboxActiveRange] = []
    segments = _action_segments(iso_path, character, action)
    for index in range(1, 5):
        run_start: int | None = None
        run_end: int | None = None
        for segment in segments:
            active = segment.hitboxes[index - 1].active
            if active and run_start is None:
                run_start = segment.start_frame
            if active:
                run_end = segment.end_frame
            elif run_start is not None and run_end is not None:
                ranges.append(HitboxActiveRange(index, run_start, run_end, run_end - run_start + 1))
                run_start = run_end = None
        if run_start is not None and run_end is not None:
            ranges.append(HitboxActiveRange(index, run_start, run_end, run_end - run_start + 1))
    return tuple(ranges)


@cache
def _action_summary(
    iso_path: Path | None,
    character: Character,
    action: Action,
) -> ActionSummary:
    """Return the :class:`ActionSummary` for one action, cached per (char, action)."""
    frame_data = _frame_data(iso_path)
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
        hitbox_active_ranges=_hitbox_active_ranges(iso_path, character, action),
    )


@cache
def _get_framedata(
    character_query: str | int,
    action_query: str | int,
    iso_path: Path | None,
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
    actions = _resolve_actions(character, action_query, iso_path)

    segments: list[FrameSegment] = []
    summaries: list[ActionSummary] = []
    for entry in actions:
        summaries.append(_action_summary(iso_path, character, entry.action))
        segments.extend(_action_segments(iso_path, character, entry.action))

    frame_data = _frame_data(iso_path)
    disc = frame_data._disc_framedata
    source = FramedataSource("csv") if disc is None else FramedataSource("iso", disc.build)

    return FramedataResult(
        character=character.name,
        character_id=int(character.value),
        character_section=character_section_name(character),
        action_query=str(action_query),
        resolved_actions=tuple(summaries),
        tags=tuple(_collect_tags(character, actions, iso_path)),
        segments=tuple(segments),
        source=source,
    )


def get_framedata(
    character_query: str | int,
    action_query: str | int,
) -> FramedataResult:
    """Return typed framedata from the configured ISO or historical CSV source.

    ``MELEE_ISO_PATH`` selects executable-backed action resolution, script
    timing, hitbox activity, and hitbox sizes. Runtime-only segment fields are
    ``None`` in that mode rather than guessed. Without the environment setting,
    this retains the historical CSV result. Results are cached by resolved
    source path and query.
    """

    return _get_framedata(character_query, action_query, _configured_iso_path())


def clear_framedata_query_caches() -> None:
    """Clear all cached high-level framedata sources and derived results."""

    _get_framedata.cache_clear()
    _action_summary.cache_clear()
    _action_segments.cache_clear()
    _available_actions.cache_clear()
    _frame_data.cache_clear()


# DESNOTE(jbarber, 2026-09-07): @lru_cache exposed these methods on the public
# callable. The source-aware wrapper cannot itself be decorated because the
# current MELEE_ISO_PATH must participate in every lookup's cache key.
get_framedata = cast(_CachedFramedataQuery, get_framedata)
get_framedata.cache_clear = clear_framedata_query_caches
get_framedata.cache_info = _get_framedata.cache_info
get_framedata.cache_parameters = _get_framedata.cache_parameters


def _attack_state_matches(
    character: Character,
    action: Action,
    frame_number: int,
    attack_state_query: str | None,
    iso_path: Path | None,
) -> bool:
    """Return whether one frame's attack state matches a query string.

    ``attack_state_query`` is matched against :meth:`FrameData.attack_state`
    names (``WINDUP``, ``ATTACKING``, ``COOLDOWN``, ``NOT_ATTACKING``). When
    ``attack_state_query is None`` the filter is suppressed.
    """
    if attack_state_query is None:
        return True
    normalized = _normalize_token(attack_state_query)
    attack = _frame_data(iso_path).attack_state(character, action, frame_number)
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

    This compatibility API always reads the historical CSV, even when
    ``MELEE_ISO_PATH`` is configured. All row values are unparsed strings. Use
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
    actions = _resolve_actions(character, action_query, None)
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
            if not _attack_state_matches(character, action, frame_number, attack_state, None):
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
