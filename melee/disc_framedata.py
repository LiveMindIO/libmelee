"""Read framedata directly from a user-supplied NTSC 1.02 Melee ISO.

This module never extracts or writes disc members. Hitbox coordinates are
bone-local DAT values; this phase does not evaluate skeletons or world geometry.
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
import threading
from dataclasses import dataclass
from pathlib import Path

from melee._gamecube import DiscImageError, GameCubeDisc
from melee._hsd_dat import DatParseError, HsdDat, parse_figatree_frame_count
from melee._ntsc102 import (
    CHARACTER_MOTION_STATE_POINTERS,
    COMMON_MOTION_STATE_COUNT,
    COMMON_MOTION_STATE_TABLE,
    DOLDECOMP_REVISION,
    FIGHTER_ACTION_COUNTS,
    FIGHTER_KINDS,
    FIGHTER_KINDS_BY_CODE,
    MOTION_STATE_SIZE,
)
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
from melee.enums import Action, Character


class DiscFrameDataError(ValueError):
    """Raised for an invalid public DiscFrameData query."""


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
    doldecomp_revision: str
    dol_offset: int
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
class MotionStateRecord:
    """One executable MotionState selected by a character/runtime action pair."""

    character: Character
    action: Action
    virtual_address: int
    dat_action_index: int | None
    motion_flags: int
    raw_move_flags: int
    move_id: int
    state_flags: int
    unknown_xa: int
    unknown_xb: int
    animation_callback: int | None
    input_callback: int | None
    physics_callback: int | None
    collision_callback: int | None
    camera_callback: int | None


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

    def frame(self, local_frame: int) -> FrameSnapshot:
        """Return a frame using libmelee's one-based action-frame convention."""

        return self.timeline.frame(local_frame)


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
        snapshot_count = 0 if frame_count <= 0 else max(1, math.ceil(frame_count) - 1)
        frames = tuple(
            FrameSnapshot(frame, float(frame - 1), (), False) for frame in range(1, snapshot_count + 1)
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
        self._codes = tuple(sorted(code for code in self._disc.fighter_members if code in FIGHTER_KINDS_BY_CODE))
        self._code_lookup = {code.casefold(): code for code in self._codes}
        self._cache: dict[str, FighterRecord] = {}
        self._motion_state_cache: dict[tuple[int, int], MotionStateRecord | None] = {}
        self._lock = threading.RLock()
        self._build = DiscBuild(
            self._disc.path.resolve(),
            "GALE01",
            0,
            2,
            "NTSC-U",
            "1.02",
            DOLDECOMP_REVISION,
            self._disc.dol_offset,
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

    def motion_state(self, character: Character, action: Action) -> MotionStateRecord | None:
        """Return the executable MotionState for a character/runtime action pair."""

        kind = character.value
        runtime_action = action.value
        if kind < 0 or kind >= len(FIGHTER_KINDS):
            raise DiscFrameDataError(f"unsupported runtime character {character!r}")
        if runtime_action < 0:
            raise DiscFrameDataError(f"invalid runtime action ID {runtime_action}")
        metadata = FIGHTER_KINDS[kind]
        if metadata.code not in self._disc.fighter_members:
            raise DiscFrameDataError(f"fighter DAT pair for runtime character {character.name} is unavailable")

        key = (kind, runtime_action)
        with self._lock:
            if key in self._motion_state_cache:
                return self._motion_state_cache[key]
            dol = self._disc.read_dol()
            executable_count = dol.u32(
                FIGHTER_ACTION_COUNTS + kind * 8 + 4,
                f"{character.name} fighter action count",
            )
            if executable_count != metadata.action_count:
                raise DiscFrameDataError(
                    f"{character.name} executable action count {executable_count} does not match "
                    f"expected NTSC 1.02 count {metadata.action_count}"
                )

            if runtime_action < COMMON_MOTION_STATE_COUNT:
                state_address = COMMON_MOTION_STATE_TABLE + runtime_action * MOTION_STATE_SIZE
            else:
                special_index = runtime_action - COMMON_MOTION_STATE_COUNT
                if special_index >= metadata.special_state_count:
                    self._motion_state_cache[key] = None
                    return None
                table_address = dol.u32(
                    CHARACTER_MOTION_STATE_POINTERS + kind * 4,
                    f"{character.name} motion-state table pointer",
                )
                if not table_address:
                    raise DiscFrameDataError(f"{character.name} has no character-specific motion-state table")
                state_address = table_address + special_index * MOTION_STATE_SIZE

            values = struct.unpack(
                ">i7I",
                dol.read(state_address, MOTION_STATE_SIZE, f"{character.name} action {runtime_action} MotionState"),
            )
            dat_index, motion_flags, raw_move_flags, *callbacks = values
            callback_names = ("animation", "input", "physics", "collision", "camera")
            for callback_name, callback in zip(callback_names, callbacks, strict=True):
                if callback and (callback % 4 or not dol.contains_executable(callback, 4)):
                    raise DiscFrameDataError(
                        f"{character.name} action {runtime_action} has {callback_name} callback "
                        f"0x{callback:X} outside an aligned executable DOL range"
                    )
            if dat_index == -1:
                mapped_index = None
            elif dat_index < 0 or dat_index >= metadata.action_count:
                raise DiscFrameDataError(
                    f"{character.name} action {runtime_action} maps to invalid DAT action index {dat_index}"
                )
            else:
                mapped_index = dat_index
            result = MotionStateRecord(
                character=character,
                action=action,
                virtual_address=state_address,
                dat_action_index=mapped_index,
                motion_flags=motion_flags,
                raw_move_flags=raw_move_flags,
                move_id=raw_move_flags >> 24,
                state_flags=(raw_move_flags >> 16) & 0xFF,
                unknown_xa=(raw_move_flags >> 8) & 0xFF,
                unknown_xb=raw_move_flags & 0xFF,
                animation_callback=callbacks[0] or None,
                input_callback=callbacks[1] or None,
                physics_callback=callbacks[2] or None,
                collision_callback=callbacks[3] or None,
                camera_callback=callbacks[4] or None,
            )
            self._motion_state_cache[key] = result
            return result

    def dat_action_index(self, character: Character, action: Action) -> int | None:
        """Map a runtime action-state ID to its fighter DAT action-table index."""

        state = self.motion_state(character, action)
        return None if state is None else state.dat_action_index

    def action_for_state(self, character: Character, action: Action) -> ActionRecord | None:
        """Return the DAT action selected by a public runtime character/action pair."""

        dat_index = self.dat_action_index(character, action)
        if dat_index is None:
            return None
        record = self.action(FIGHTER_KINDS[character.value].code, dat_index)
        if character is Character.NANA and not record.animation_size:
            record = self.action(FIGHTER_KINDS[Character.POPO.value].code, dat_index)
        return record if record.animation_size or record.script_data_offset is not None else None

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
        metadata = FIGHTER_KINDS_BY_CODE[code]
        for raw in dat.fighter_actions(expected_root=metadata.root_symbol, expected_count=metadata.action_count):
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
    "MotionStateRecord",
    "RawCommand",
    "SubactionParseError",
    "ThrowEvent",
]
