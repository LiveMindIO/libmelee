"""Read framedata directly from a user-supplied NTSC 1.02 Melee ISO.

This module never extracts or writes disc members. Hitbox coordinates are
bone-local DAT values; this phase does not evaluate skeletons or world geometry.
"""

from __future__ import annotations

import hashlib
import math
import os
import threading
from dataclasses import dataclass
from pathlib import Path

from melee._gamecube import DiscImageError, GameCubeDisc
from melee._hsd_dat import DatParseError, HsdDat, parse_figatree_frame_count
from melee._subaction import (
    ActionTimeline,
    ExecutedCommand,
    FrameSnapshot,
    Hitbox,
    HitboxChange,
    HitboxEvent,
    HitboxGeneration,
    HurtScope,
    HurtState,
    HurtStateEvent,
    RawCommand,
    SubactionParseError,
    ThrowEvent,
    interpret_subaction,
)


class DiscFrameDataError(ValueError):
    """Raised for an invalid public DiscFrameData query."""


# Root symbols and action counts are build-specific executable metadata.
_FIGHTER_METADATA = {
    "Mr": ("ftDataMario", 303),
    "Fx": ("ftDataFox", 327),
    "Ca": ("ftDataCaptain", 318),
    "Dk": ("ftDataDonkey", 337),
    "Kb": ("ftDataKirby", 479),
    "Kp": ("ftDataKoopa", 316),
    "Lk": ("ftDataLink", 314),
    "Sk": ("ftDataSeak", 317),
    "Ns": ("ftDataNess", 326),
    "Pe": ("ftDataPeach", 318),
    "Pp": ("ftDataPopo", 321),
    "Nn": ("ftDataNana", 321),
    "Pk": ("ftDataPikachu", 320),
    "Ss": ("ftDataSamus", 313),
    "Ys": ("ftDataYoshi", 314),
    "Pr": ("ftDataPurin", 327),
    "Mt": ("ftDataMewtwo", 314),
    "Lg": ("ftDataLuigi", 312),
    "Ms": ("ftDataMars", 327),
    "Zd": ("ftDataZelda", 311),
    "Cl": ("ftDataClink", 314),
    "Dr": ("ftDataDrmario", 303),
    "Fc": ("ftDataFalco", 327),
    "Pc": ("ftDataPichu", 320),
    "Gw": ("ftDataGamewatch", 323),
    "Gn": ("ftDataGanon", 318),
    "Fe": ("ftDataEmblem", 327),
    "Mh": ("ftDataMasterhand", 345),
    "Ch": ("ftDataCrazyhand", 344),
    "Bo": ("ftDataBoy", 295),
    "Gl": ("ftDataGirl", 295),
    "Gk": ("ftDataGkoopa", 316),
    "Sb": ("ftDataSandbag", 296),
}
_MAX_TIMELINE_FRAMES = 10_000


@dataclass(frozen=True, slots=True)
class DiscBuild:
    """Disc identity and filesystem provenance for all returned data."""

    iso_path: Path
    game_id: str
    disc_number: int
    revision: int
    region: str
    version: str
    fst_offset: int
    fst_size: int


@dataclass(frozen=True, slots=True)
class FighterSource:
    """Exact ISO members and content hashes used for one fighter."""

    code: str
    fighter_dat_member: str
    animation_dat_member: str
    fighter_dat_sha256: str
    animation_dat_sha256: str


@dataclass(frozen=True, slots=True)
class ActionRecord:
    """One DAT action-table entry and its interpreted script timeline.

    ``dat_action_index`` is an index in the fighter DAT and is not always equal
    to :class:`melee.enums.Action` or ``PlayerState.action``.
    """

    dat_action_index: int
    symbol: str | None
    animation_offset: int
    animation_size: int
    animation_frame_count: float | None
    script_data_offset: int | None
    script_dat_offset: int | None
    raw_flags: int
    runtime_animation_pointer: int
    timeline: ActionTimeline


@dataclass(frozen=True, slots=True)
class FighterRecord:
    """Immutable source and action records for a two-character fighter code."""

    code: str
    source: FighterSource
    actions: tuple[ActionRecord, ...]

    def action(self, dat_action_index: int) -> ActionRecord:
        """Return an action by DAT table index, not runtime action-state ID."""

        if dat_action_index < 0 or dat_action_index >= len(self.actions):
            raise DiscFrameDataError(
                f"fighter {self.code!r} has no DAT action index {dat_action_index}; "
                f"valid range is 0..{len(self.actions) - 1}"
            )
        return self.actions[dat_action_index]


def _empty_timeline(frame_count: float | None) -> ActionTimeline:
    frames = ()
    if frame_count is not None:
        if frame_count > _MAX_TIMELINE_FRAMES:
            raise SubactionParseError(f"empty subaction: frame guard exceeded {_MAX_TIMELINE_FRAMES} frames")
        frames = tuple(
            FrameSnapshot(frame, float(frame - 1), (), False) for frame in range(1, max(0, math.ceil(frame_count)) + 1)
        )
    return ActionTimeline((), (), (), (), (), None, None, frames, False, False, False)


class DiscFrameData:
    """ISO-backed, read-only framedata for a legal NTSC 1.02 disc image.

    Fighter DAT/AJ members are read directly from the ISO and parsed lazily on
    the first query for each fighter. No Nintendo data is extracted or written.
    Geometry in returned hitboxes is bone-local and cannot be treated as world
    or fighter-root geometry without animation and skeleton evaluation.
    """

    def __init__(self, iso_path: str | os.PathLike[str]):
        self._disc = GameCubeDisc(iso_path)
        self._codes = tuple(sorted(code for code in self._disc.fighter_members if code in _FIGHTER_METADATA))
        self._code_lookup = {code.casefold(): code for code in self._codes}
        self._cache: dict[str, FighterRecord] = {}
        self._lock = threading.RLock()
        self._build = DiscBuild(
            self._disc.path.resolve(),
            "GALE01",
            0,
            2,
            "NTSC-U",
            "1.02",
            self._disc.fst_offset,
            self._disc.fst_size,
        )

    @property
    def build(self) -> DiscBuild:
        """Return immutable disc/build provenance."""

        return self._build

    @property
    def source(self) -> DiscBuild:
        """Alias for the immutable disc source and build provenance."""

        return self._build

    @property
    def available_fighter_codes(self) -> tuple[str, ...]:
        """Two-character codes having both an exact base DAT and AJ DAT."""

        return self._codes

    def fighter(self, code: str) -> FighterRecord:
        """Return lazily parsed framedata for a two-character fighter code."""

        canonical = self._code_lookup.get(code.casefold())
        if canonical is None:
            available = ", ".join(self._codes) or "none"
            raise DiscFrameDataError(f"fighter code {code!r} is unavailable; available codes: {available}")
        with self._lock:
            cached = self._cache.get(canonical)
            if cached is None:
                cached = self._parse_fighter(canonical)
                self._cache[canonical] = cached
            return cached

    def actions(self, code: str) -> tuple[ActionRecord, ...]:
        """Return all records in a fighter's DAT action-table order."""

        return self.fighter(code).actions

    def action(self, code: str, dat_action_index: int) -> ActionRecord:
        """Query by fighter code and DAT index, not ``PlayerState.action``."""

        return self.fighter(code).action(dat_action_index)

    def _parse_fighter(self, code: str) -> FighterRecord:
        dat_member, aj_member = self._disc.fighter_members[code]
        fighter_bytes = self._disc.read_member(dat_member)
        animation_bytes = self._disc.read_member(aj_member)
        source = FighterSource(
            code,
            dat_member.path,
            aj_member.path,
            hashlib.sha256(fighter_bytes).hexdigest(),
            hashlib.sha256(animation_bytes).hexdigest(),
        )
        dat = HsdDat(fighter_bytes, context=dat_member.path)
        actions = []
        animation_frame_counts: dict[tuple[int, int, str], float] = {}
        root_name, action_count = _FIGHTER_METADATA[code]
        for raw in dat.fighter_actions(expected_root=root_name, expected_count=action_count):
            frame_count = None
            if raw.animation_size:
                if raw.symbol is None:
                    raise DatParseError(f"{dat_member.path}: action {raw.index} has animation data but no symbol")
                if (
                    raw.animation_offset > len(animation_bytes)
                    or raw.animation_size > len(animation_bytes) - raw.animation_offset
                ):
                    raise DatParseError(
                        f"{dat_member.path}: action {raw.index} animation range "
                        f"0x{raw.animation_offset:X}+0x{raw.animation_size:X} exceeds {aj_member.path}"
                    )
                animation_key = (raw.animation_offset, raw.animation_size, raw.symbol)
                frame_count = animation_frame_counts.get(animation_key)
                if frame_count is None:
                    embedded = animation_bytes[raw.animation_offset : raw.animation_offset + raw.animation_size]
                    frame_count = parse_figatree_frame_count(
                        embedded,
                        expected_root=raw.symbol,
                        context=f"{aj_member.path} action {raw.index} at 0x{raw.animation_offset:X}",
                    )
                    animation_frame_counts[animation_key] = frame_count
            timeline = (
                interpret_subaction(
                    dat.data,
                    raw.script_data_offset,
                    pointer_locations=dat.pointer_locations,
                    animation_frame_count=frame_count,
                    context=f"{dat_member.path} action {raw.index}",
                    max_frames=_MAX_TIMELINE_FRAMES,
                    truncate_at_max_frames=True,
                )
                if raw.script_data_offset is not None
                else _empty_timeline(frame_count)
            )
            actions.append(
                ActionRecord(
                    raw.index,
                    raw.symbol,
                    raw.animation_offset,
                    raw.animation_size,
                    frame_count,
                    raw.script_data_offset,
                    raw.script_data_offset + 0x20 if raw.script_data_offset is not None else None,
                    raw.flags,
                    raw.runtime_animation_pointer,
                    timeline,
                )
            )
        return FighterRecord(code, source, tuple(actions))


__all__ = [
    "ActionRecord",
    "ActionTimeline",
    "DatParseError",
    "DiscBuild",
    "DiscFrameData",
    "DiscFrameDataError",
    "DiscImageError",
    "ExecutedCommand",
    "FighterRecord",
    "FighterSource",
    "FrameSnapshot",
    "Hitbox",
    "HitboxChange",
    "HitboxEvent",
    "HitboxGeneration",
    "HurtScope",
    "HurtState",
    "HurtStateEvent",
    "RawCommand",
    "SubactionParseError",
    "ThrowEvent",
]
