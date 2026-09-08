"""Read framedata directly from a user-supplied NTSC 1.02 Melee ISO.

This module never extracts or writes disc members. It exposes bone-local DAT
values plus explicitly static animation-root and fighter-pose evaluations.
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
import threading
from dataclasses import dataclass
from pathlib import Path

from melee._gamecube import DiscImageError, FstEntry, GameCubeDisc
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
from melee._pose import (
    FigaTree,
    FighterParts,
    FighterPoseSource,
    Vec3,
    animation_root_translation,
    parse_figatree,
    parse_fighter_parts,
    parse_fighter_pose_source,
    pose_matrices,
    retail_fixed_point,
    transform_point,
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


_MAX_TIMELINE_COMMANDS = 100_000
_MAX_TIMELINE_FRAMES = 10_000
_MAX_FIGHTER_TIMELINE_ITEMS = _MAX_TIMELINE_COMMANDS + _MAX_TIMELINE_FRAMES
_ANIMATION_LOOP_FLAG = 0x40000000
_ANIMATION_FRAME_ACCUMULATION_FLAG = 0x20000000
_ANIMATION_ROOT_MOTION_FLAG = 0x80000000
_ANIMATION_SECONDARY_ROOT_FLAG = 0x04000000
_ANIMATION_ROOT_MODEL_SCALE_ONLY_FLAG = 0x02000000


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

    @property
    def animation_loops(self) -> bool:
        """Whether the DAT record allows animation time to wrap at its endpoint."""

        return bool(self.raw_flags & _ANIMATION_LOOP_FLAG)

    @property
    def animation_root_motion_enabled(self) -> bool:
        """Whether retail extracts TransN translation for animation-induced physics."""

        return bool(self.raw_flags & _ANIMATION_ROOT_MOTION_FLAG)

    @property
    def animation_uses_secondary_root(self) -> bool:
        """Whether retail selects TransN2 as the effective animation root."""

        return bool(self.raw_flags & _ANIMATION_SECONDARY_ROOT_FLAG)

    @property
    def animation_root_uses_fighter_scale(self) -> bool:
        """Whether dynamic fighter scale participates in root-translation scaling."""

        return not bool(self.raw_flags & _ANIMATION_ROOT_MODEL_SCALE_ONLY_FLAG)


@dataclass(frozen=True, slots=True)
class PosedHitbox:
    """One fighter-owned hitbox transformed into fighter-root coordinates."""

    hitbox: Hitbox
    size: float
    x: float
    y: float
    z: float


@dataclass(frozen=True, slots=True)
class PosedFrame:
    """Static unblended pose sampled using one-based public action frames."""

    local_frame: int
    animation_time: float
    hitboxes: tuple[PosedHitbox, ...]


@dataclass(frozen=True, slots=True)
class AnimationRootTranslation:
    """Retail-scaled absolute or delta translation in TransN local axes."""

    lateral: float
    """TRAX translation, not ordinary horizontal gameplay movement."""

    vertical: float
    """TRAY translation."""

    forward: float
    """TRAZ translation, projected through fighter facing for horizontal use."""


@dataclass(frozen=True, slots=True)
class AnimationRootFrame:
    """Nominal unit-rate animation-root sample before gameplay callbacks."""

    local_frame: int
    animation_time: float
    animation_root_enabled: bool
    uses_secondary_translation: bool
    fighter_scale_applied: bool
    translation: AnimationRootTranslation
    delta: AnimationRootTranslation
    projected_horizontal_delta: float


@dataclass(frozen=True, slots=True)
class _AnimationContext:
    record: ActionRecord
    source: FighterPoseSource
    tree: FigaTree
    source_kind: int
    additional_bones: int
    animation_time: float


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


def _float32(value: float) -> float:
    return struct.unpack(">f", struct.pack(">f", value))[0]


def _checked_float32(value: float, name: str) -> float:
    try:
        rounded = _float32(value)
    except OverflowError as exc:
        raise DiscFrameDataError(f"{name} must fit a finite float32; got {value!r}") from exc
    if not math.isfinite(rounded):
        raise DiscFrameDataError(f"{name} must fit a finite float32; got {value!r}")
    return rounded


def _validate_fighter_scale(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise DiscFrameDataError(f"fighter_scale must be finite and positive; got {value!r}")
    try:
        rounded = _float32(value)
    except OverflowError as exc:
        raise DiscFrameDataError(f"fighter_scale must fit a finite float32; got {value!r}") from exc
    if rounded <= 0:
        raise DiscFrameDataError(f"fighter_scale must remain positive as float32; got {value!r}")
    return rounded


class DiscFrameData:
    """ISO-backed, read-only framedata for a legal NTSC 1.02 disc image.

    Fighter DAT/AJ members are read directly from the ISO and parsed lazily on
    the first query for each fighter. No Nintendo data is extracted or written.
    Geometry in returned hitboxes is bone-local and cannot be treated as world
    or fighter-root geometry without animation and skeleton evaluation.
    """

    def __init__(self, iso_path: str | os.PathLike[str]):
        self._disc = GameCubeDisc(iso_path)
        self._disc.read_dol()
        self._codes = tuple(sorted(code for code in self._disc.fighter_members if code in FIGHTER_KINDS_BY_CODE))
        self._code_lookup = {code.casefold(): code for code in self._codes}
        self._cache: dict[str, FighterRecord] = {}
        self._motion_state_cache: dict[tuple[int, int], MotionStateRecord | None] = {}
        self._fighter_parts: tuple[FighterParts, ...] | None = None
        self._pose_cache: dict[str, FighterPoseSource] = {}
        self._figatree_cache: dict[tuple[str, int], FigaTree] = {}
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

        resolved = self._action_and_code_for_state(character, action)
        return None if resolved is None else resolved[0]

    def _action_and_code_for_state(
        self,
        character: Character,
        action: Action,
    ) -> tuple[ActionRecord, str] | None:
        dat_index = self.dat_action_index(character, action)
        if dat_index is None:
            return None
        code = FIGHTER_KINDS[character.value].code
        record = self.action(code, dat_index)
        if character is Character.NANA and not record.animation_size:
            code = FIGHTER_KINDS[Character.POPO.value].code
            record = self.action(code, dat_index)
        return (record, code) if record.animation_size or record.script_data_offset is not None else None

    def posed_frame(
        self,
        character: Character,
        action: Action,
        local_frame: int,
        *,
        fighter_scale: float = 1.0,
        facing: int = 1,
    ) -> PosedFrame:
        """Return fighter-owned hitboxes in fighter-root coordinates.

        This deterministic static view starts an unblended action at animation
        time zero and advances it at unit speed. Runtime callbacks, articles,
        transition blending, and dynamic bones are outside this contract.
        """

        if local_frame < 1:
            raise DiscFrameDataError(f"action frames are one-indexed; got {local_frame}")
        fighter_scale = _validate_fighter_scale(fighter_scale)
        if facing not in (-1, 1):
            raise DiscFrameDataError(f"facing must be -1 or 1; got {facing!r}")
        context = self._animation_context(character, action, local_frame)
        snapshot = context.record.frame(local_frame)
        try:
            matrices = pose_matrices(
                context.source,
                context.tree,
                fighter_kind=character.value,
                source_kind=context.source_kind,
                additional_bones=context.additional_bones,
                raw_action_flags=context.record.raw_flags,
                animation_time=context.animation_time,
                fighter_scale=fighter_scale,
                facing=facing,
            )
        except DatParseError as exc:
            raise DiscFrameDataError(str(exc)) from exc
        root_matrix = matrices[0]
        assert root_matrix is not None
        root = transform_point(root_matrix, Vec3(0.0, 0.0, 0.0))
        target_parts = context.source.parts[character.value]
        posed = []
        for hitbox in snapshot.active_hitboxes:
            bone = hitbox.bone_id
            if hitbox.use_common_bone_ids:
                if bone >= len(target_parts.part_to_joint):
                    raise DiscFrameDataError(
                        f"{character.name} {action.name} hitbox {hitbox.hitbox_id} has invalid common bone {bone}"
                    )
                bone = target_parts.part_to_joint[bone]
            if bone == 0xFF or bone >= len(matrices) or matrices[bone] is None:
                raise DiscFrameDataError(
                    f"{character.name} {action.name} hitbox {hitbox.hitbox_id} uses unavailable fighter bone "
                    f"{hitbox.bone_id}"
                )
            local_scale = fighter_scale if hitbox.ignore_fighter_scale else 1.0
            local = Vec3(
                retail_fixed_point(hitbox.bone_local_x) / local_scale,
                retail_fixed_point(hitbox.bone_local_y) / local_scale,
                retail_fixed_point(hitbox.bone_local_z) / local_scale,
            )
            matrix = matrices[bone]
            assert matrix is not None
            world = transform_point(matrix, local)
            posed.append(
                PosedHitbox(
                    hitbox,
                    retail_fixed_point(hitbox.size) * fighter_scale,
                    world.x - root.x,
                    world.y - root.y,
                    world.z - root.z,
                )
            )
        return PosedFrame(local_frame, context.animation_time, tuple(posed))

    def animation_root_frame(
        self,
        character: Character,
        action: Action,
        local_frame: int,
        *,
        fighter_scale: float = 1.0,
        facing: int = 1,
    ) -> AnimationRootFrame:
        """Return nominal TransN animation input for one unit-rate frame.

        Translation channels are absolute local animation values. ``delta`` is
        the retail-scaled difference between samples at times ``local_frame``
        and ``local_frame - 1``. Runtime callbacks, blending, velocity, and
        collision decide whether that input becomes fighter displacement.
        """

        if local_frame < 1:
            raise DiscFrameDataError(f"action frames are one-indexed; got {local_frame}")
        fighter_scale = _validate_fighter_scale(fighter_scale)
        if facing not in (-1, 1):
            raise DiscFrameDataError(f"facing must be -1 or 1; got {facing!r}")
        context = self._animation_context(character, action, local_frame)
        previous_time = float(local_frame - 1)
        if context.record.animation_loops and context.tree.frame_count > 0:
            previous_time %= context.tree.frame_count
        try:
            current = animation_root_translation(
                context.source,
                context.tree,
                fighter_kind=character.value,
                source_kind=context.source_kind,
                additional_bones=context.additional_bones,
                raw_action_flags=context.record.raw_flags,
                animation_time=context.animation_time,
                fighter_scale=fighter_scale,
            )
            previous = animation_root_translation(
                context.source,
                context.tree,
                fighter_kind=character.value,
                source_kind=context.source_kind,
                additional_bones=context.additional_bones,
                raw_action_flags=context.record.raw_flags,
                animation_time=previous_time,
                fighter_scale=fighter_scale,
            )
        except DatParseError as exc:
            raise DiscFrameDataError(str(exc)) from exc
        translation = AnimationRootTranslation(current.x, current.y, current.z)
        delta = AnimationRootTranslation(
            _checked_float32(current.x - previous.x, "animation-root delta"),
            _checked_float32(current.y - previous.y, "animation-root delta"),
            _checked_float32(current.z - previous.z, "animation-root delta"),
        )
        return AnimationRootFrame(
            local_frame=local_frame,
            animation_time=context.animation_time,
            animation_root_enabled=context.record.animation_root_motion_enabled,
            uses_secondary_translation=context.record.animation_uses_secondary_root,
            fighter_scale_applied=context.record.animation_root_uses_fighter_scale,
            translation=translation,
            delta=delta,
            projected_horizontal_delta=_checked_float32(
                delta.forward * facing,
                "projected animation-root delta",
            ),
        )

    def _animation_context(
        self,
        character: Character,
        action: Action,
        local_frame: int,
    ) -> _AnimationContext:
        """Resolve one validated static animation sample."""

        if local_frame < 1:
            raise DiscFrameDataError(f"action frames are one-indexed; got {local_frame}")
        resolved = self._action_and_code_for_state(character, action)
        if resolved is None:
            raise DiscFrameDataError(f"{character.name} {action.name} has no fighter animation")
        record, animation_code = resolved
        if not record.animation_size or record.symbol is None:
            raise DiscFrameDataError(f"{character.name} {action.name} has no fighter animation")
        try:
            record.frame(local_frame)
        except IndexError as exc:
            raise DiscFrameDataError(
                f"{character.name} {action.name} has no extracted script snapshot for frame {local_frame}"
            ) from exc
        metadata = FIGHTER_KINDS[character.value]
        source = self._fighter_pose_source(metadata.code, character.value)
        tree = self._figatree(animation_code, record)
        source_kind = record.raw_flags & 0x3F
        if source_kind >= len(source.parts):
            raise DiscFrameDataError(
                f"{character.name} {action.name} selects unsupported animation source kind {source_kind}"
            )
        animation_time = float(local_frame)
        if record.animation_loops and tree.frame_count > 0:
            animation_time %= tree.frame_count
        return _AnimationContext(
            record,
            source,
            tree,
            source_kind,
            (record.raw_flags & 0x003FFE00) >> 9,
            animation_time,
        )

    def _figatree(self, code: str, record: ActionRecord) -> FigaTree:
        key = (code, record.dat_action_index)
        with self._lock:
            cached = self._figatree_cache.get(key)
            if cached is not None:
                return cached
            _, animation_member = self._disc.fighter_members[code]
            animation_data = self._disc.read_member(animation_member)
            embedded = animation_data[
                record.animation_offset : record.animation_offset + record.animation_size
            ]
            tree = parse_figatree(
                embedded,
                expected_root=record.symbol,
                context=f"{animation_member.path} action {record.dat_action_index} pose",
            )
            self._figatree_cache[key] = tree
            return tree

    def _fighter_pose_source(self, code: str, fighter_kind: int) -> FighterPoseSource:
        with self._lock:
            cached = self._pose_cache.get(code)
            if cached is not None:
                return cached
            if self._fighter_parts is None:
                common_member = self._unique_member("PlCo.dat")
                self._fighter_parts = parse_fighter_parts(
                    HsdDat(self._disc.read_member(common_member), context=common_member.path)
                )
            fighter_member, _ = self._disc.fighter_members[code]
            costume_member = self._unique_member(f"Pl{code}Nr.dat")
            source = parse_fighter_pose_source(
                HsdDat(self._disc.read_member(fighter_member), context=fighter_member.path),
                HsdDat(self._disc.read_member(costume_member), context=costume_member.path),
                self._fighter_parts,
                fighter_kind,
            )
            self._pose_cache[code] = source
            return source

    def _unique_member(self, name: str) -> FstEntry:
        matches = [entry for entry in self._disc.entries if not entry.is_directory and entry.name == name]
        if len(matches) != 1:
            raise DiscFrameDataError(f"disc must contain exactly one {name!r} member; found {len(matches)}")
        return matches[0]

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
        timeline_cache: dict[tuple[int | None, float | None, bool, bool], ActionTimeline] = {}
        retained_timeline_items = 0
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
            animation_loops = bool(raw.flags & _ANIMATION_LOOP_FLAG)
            animation_frame_accumulates = bool(raw.flags & _ANIMATION_FRAME_ACCUMULATION_FLAG)
            timeline_key = (raw.script_data_offset, frame_count, animation_loops, animation_frame_accumulates)
            timeline = timeline_cache.get(timeline_key)
            if timeline is None:
                context = f"{dat_member.path} action {raw.index}"
                timeline = (
                    interpret_subaction(
                        dat.data,
                        raw.script_data_offset,
                        pointer_locations=dat.pointer_locations,
                        animation_frame_count=frame_count,
                        animation_loops=animation_loops,
                        animation_frame_accumulates=animation_frame_accumulates,
                        context=context,
                        max_commands=_MAX_TIMELINE_COMMANDS,
                        max_frames=_MAX_TIMELINE_FRAMES,
                        truncate_at_max_frames=True,
                    )
                    if raw.script_data_offset is not None
                    else _empty_timeline(frame_count)
                )
                timeline_items = len(timeline.commands) + len(timeline.frames)
                if timeline_items > _MAX_FIGHTER_TIMELINE_ITEMS - retained_timeline_items:
                    raise SubactionParseError(
                        f"{context}: aggregate fighter timeline guard exceeded "
                        f"{_MAX_FIGHTER_TIMELINE_ITEMS} retained commands and frames"
                    )
                retained_timeline_items += timeline_items
                timeline_cache[timeline_key] = timeline
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
    "AnimationRootFrame",
    "AnimationRootTranslation",
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
    "PosedFrame",
    "PosedHitbox",
    "RawCommand",
    "SubactionParseError",
    "ThrowEvent",
]
