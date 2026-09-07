"""Static fighter-pose evaluation for ISO-backed framedata."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, replace

from melee._hsd_dat import DatParseError, HsdDat

_JOBJ_CLASSICAL_SCALING = 1 << 3
_JOBJ_INSTANCE = 1 << 12
_MAX_FIGHTER_PARTS = 0x8C
_MAX_FOBJ_KEYS = 65_536
_COMMON_PART_COUNT = 54
_PART_TRANS_N = 1
_FULL_TRANSLATION_PARTS = frozenset((0, 1, 2, 3, 4, 53))
_ANIMATION_ROOT_MOTION = 0x80000000
# DESNOTE(jbarber, 2026-09-06): Retail multiplies these script integers by the
# nearest stored float to 0.003906 rather than exact 1/256. See ftAction_8007121C:
# https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/ftaction.c#L289-L347
_RETAIL_FIXED_POINT_SCALE = struct.unpack(">f", struct.pack(">f", 0.003906))[0]


@dataclass(frozen=True, slots=True)
class Vec3:
    x: float
    y: float
    z: float


@dataclass(frozen=True, slots=True)
class Joint:
    parent_index: int | None
    flags: int
    rotation: Vec3
    scale: Vec3
    translation: Vec3


@dataclass(frozen=True, slots=True)
class FighterParts:
    joint_to_part: tuple[int, ...]
    part_to_joint: tuple[int, ...]
    optional_parts: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class AnimationKey:
    frame: int
    value: float | None
    tangent: float | None
    interpolation: int


@dataclass(frozen=True, slots=True)
class AnimationTrack:
    start_frame: int
    track_type: int
    keys: tuple[AnimationKey, ...]

    def value_at(self, animation_time: float) -> float | None:
        """Evaluate one retail FOBJ track from its reset state."""

        time = animation_time + self.start_frame
        if time < 0 or not self.keys:
            return None

        p0 = p1 = d0 = d1 = t0 = t1 = 0.0
        interpolation = segment_interpolation = 1
        saw_value = False
        for key in self.keys:
            segment_interpolation = interpolation
            interpolation = key.interpolation
            if interpolation in (1, 2):
                p0 = p1
                assert key.value is not None
                p1 = key.value
                saw_value = True
                if segment_interpolation != 5:
                    d0, d1 = d1, 0.0
                t0, t1 = t1, float(key.frame)
            elif interpolation == 3:
                p0, d0 = p1, d1
                assert key.value is not None
                p1, d1 = key.value, 0.0
                saw_value = True
                t0, t1 = t1, float(key.frame)
            elif interpolation == 4:
                p0 = p1
                assert key.value is not None and key.tangent is not None
                p1, d0, d1 = key.value, d1, key.tangent
                saw_value = True
                t0, t1 = t1, float(key.frame)
            elif interpolation == 5:
                assert key.tangent is not None
                d0, d1 = d1, key.tangent
            elif interpolation == 6:
                assert key.value is not None
                p0 = p1 = key.value
                saw_value = True
            if t1 > time and interpolation != 5:
                break
            segment_interpolation = interpolation
        if not saw_value:
            return None
        if time <= t0:
            return p0
        if time >= t1:
            return p1
        if t0 == t1 or segment_interpolation in (1, 6):
            return p0
        elapsed = time - t0
        duration = t1 - t0
        if segment_interpolation == 2:
            return p0 + (p1 - p0) * elapsed / duration
        inverse_duration = 1.0 / duration
        elapsed_squared = elapsed * elapsed
        first = inverse_duration * inverse_duration * elapsed_squared * elapsed
        third = 3.0 * elapsed_squared * inverse_duration * inverse_duration
        fourth = first - elapsed_squared * inverse_duration
        first = 2.0 * first * inverse_duration
        return (
            d1 * fourth
            + d0 * (elapsed + fourth - elapsed_squared * inverse_duration)
            + p0 * (1.0 + first - third)
            + p1 * (-first + third)
        )


@dataclass(frozen=True, slots=True)
class AnimationNode:
    tracks: tuple[AnimationTrack, ...]


@dataclass(frozen=True, slots=True)
class FigaTree:
    type: int
    flags: int
    frame_count: float
    nodes: tuple[AnimationNode, ...]


@dataclass(frozen=True, slots=True)
class FighterPoseSource:
    joints: tuple[Joint | None, ...]
    parts: tuple[FighterParts, ...]
    model_scale: float
    special_bone: int


def retail_fixed_point(value: float) -> float:
    """Apply the retail runtime's approximate 1/256 float conversion."""

    raw = round(value * 256.0)
    return _float32(_float32(float(raw)) * _RETAIL_FIXED_POINT_SCALE)


def parse_figatree(
    data: bytes,
    *,
    expected_root: str | None = None,
    context: str = "animation DAT",
) -> FigaTree:
    dat = HsdDat(data, context=context)
    roots = [
        root
        for root in dat.roots
        if (root.name == expected_root if expected_root is not None else root.name.endswith("_figatree"))
    ]
    if len(roots) != 1:
        wanted = repr(expected_root) if expected_root is not None else "one _figatree public root"
        raise DatParseError(f"{context}: expected {wanted}, found {len(roots)} matching public roots")
    root = roots[0].data_offset
    dat.require_range(root, 0x14, "FigaTree")
    tree_type, flags, frame_count = struct.unpack_from(">iIf", dat.data, root)
    if not math.isfinite(frame_count) or frame_count < 0:
        raise DatParseError(f"{context}: invalid FigaTree frame count {frame_count!r}")
    node_counts = dat.pointer(root + 0x0C, nullable=False, description="FigaTree node-count table")
    tracks_offset = dat.pointer(root + 0x10, nullable=False, description="FigaTree track table")
    assert node_counts is not None
    assert tracks_offset is not None

    counts = []
    count_limit = min(dat.next_object_offset(node_counts), dat.data_size)
    while node_counts + len(counts) < count_limit:
        count = dat.data[node_counts + len(counts)]
        if count == 0xFF:
            break
        counts.append(count)
        if len(counts) > _MAX_FIGHTER_PARTS:
            raise DatParseError(f"{context}: FigaTree exceeds {_MAX_FIGHTER_PARTS} fighter parts")
    else:
        raise DatParseError(f"{context}: FigaTree node-count table is not terminated")

    total_tracks = sum(counts)
    dat.require_range(tracks_offset, total_tracks * 0x0C, "FigaTree track table")
    nodes = []
    track_index = 0
    for count in counts:
        tracks = []
        for _ in range(count):
            offset = tracks_offset + track_index * 0x0C
            data_length, start_frame, track_type, value_format, tangent_format = struct.unpack_from(
                ">HhBBB", dat.data, offset
            )
            buffer_offset = dat.pointer(offset + 8, nullable=False, description="FigaTree track data")
            assert buffer_offset is not None
            dat.require_range(buffer_offset, data_length, "FigaTree track data")
            keys = _decode_track(
                dat.data[buffer_offset : buffer_offset + data_length],
                value_format,
                tangent_format,
                context,
            )
            tracks.append(AnimationTrack(start_frame, track_type, keys))
            track_index += 1
        nodes.append(AnimationNode(tuple(tracks)))
    return FigaTree(tree_type, flags, frame_count, tuple(nodes))


def parse_fighter_parts(dat: HsdDat, *, fighter_kind_count: int = 34) -> tuple[FighterParts, ...]:
    roots = [root for root in dat.roots if root.name == "ftLoadCommonData"]
    if len(roots) != 1:
        raise DatParseError(f"{dat.context}: expected one 'ftLoadCommonData' root, found {len(roots)}")
    root = roots[0].data_offset
    parts_array = dat.pointer(root + 0x10, nullable=False, description="fighter parts table array")
    optional_array = dat.pointer(root + 0x14, nullable=False, description="optional fighter parts array")
    assert parts_array is not None
    assert optional_array is not None
    dat.require_range(parts_array, fighter_kind_count * 4, "fighter parts table array")
    dat.require_range(optional_array, fighter_kind_count * 4, "optional fighter parts array")

    result = []
    for fighter_kind in range(fighter_kind_count):
        table = dat.pointer(parts_array + fighter_kind * 4, nullable=False, description="fighter parts table")
        assert table is not None
        joint_to_part = dat.pointer(table, nullable=False, description="joint-to-part table")
        part_to_joint = dat.pointer(table + 4, nullable=False, description="part-to-joint table")
        parts_count = dat.u32(table + 8)
        assert joint_to_part is not None
        assert part_to_joint is not None
        if not 0 < parts_count <= _MAX_FIGHTER_PARTS:
            raise DatParseError(f"{dat.context}: fighter kind {fighter_kind} has invalid part count {parts_count}")
        dat.require_range(joint_to_part, parts_count, "joint-to-part table")
        dat.require_range(part_to_joint, _COMMON_PART_COUNT, "part-to-joint table")

        optional = dat.pointer(optional_array + fighter_kind * 4, description="optional fighter parts")
        optional_parts: list[int] = []
        if optional is not None:
            entries = dat.pointer(optional, nullable=False, description="optional fighter part entries")
            entries_count = dat.u32(optional + 4)
            assert entries is not None
            if entries_count > _MAX_FIGHTER_PARTS:
                raise DatParseError(
                    f"{dat.context}: fighter kind {fighter_kind} has {entries_count} optional-part entries"
                )
            dat.require_range(entries, entries_count * 4, "optional fighter part entries")
            optional_parts = [dat.data[entries + index * 4] for index in range(entries_count)]
            if len(set(optional_parts)) != len(optional_parts):
                raise DatParseError(f"{dat.context}: fighter kind {fighter_kind} repeats an optional part")
            if any(part >= parts_count for part in optional_parts):
                raise DatParseError(f"{dat.context}: fighter kind {fighter_kind} has an invalid optional part")
        result.append(
            FighterParts(
                tuple(dat.data[joint_to_part : joint_to_part + parts_count]),
                tuple(dat.data[part_to_joint : part_to_joint + _COMMON_PART_COUNT]),
                tuple(optional_parts),
            )
        )
    return tuple(result)


def parse_fighter_pose_source(
    fighter_dat: HsdDat,
    costume_dat: HsdDat,
    parts: tuple[FighterParts, ...],
    fighter_kind: int,
) -> FighterPoseSource:
    roots = [root for root in fighter_dat.roots if root.name.startswith("ftData")]
    if len(roots) != 1:
        raise DatParseError(f"{fighter_dat.context}: expected one ftData root, found {len(roots)}")
    fighter = roots[0].data_offset
    attributes = fighter_dat.pointer(fighter, nullable=False, description="fighter common attributes")
    model_lookup = fighter_dat.pointer(fighter + 8, nullable=False, description="fighter model lookup")
    assert attributes is not None
    assert model_lookup is not None
    fighter_dat.require_range(attributes, 0x90, "fighter common attributes")
    fighter_dat.require_range(model_lookup, 0x15, "fighter model lookup")
    model_scale = struct.unpack_from(">f", fighter_dat.data, attributes + 0x8C)[0]
    if not math.isfinite(model_scale) or model_scale <= 0:
        raise DatParseError(f"{fighter_dat.context}: invalid model scale {model_scale!r}")
    special_bone = fighter_dat.data[model_lookup + 0x10]

    joint_roots = [root for root in costume_dat.roots if root.name.endswith("_Share_joint")]
    if len(joint_roots) != 1:
        raise DatParseError(f"{costume_dat.context}: expected one _Share_joint root, found {len(joint_roots)}")
    flat_joints = _parse_joint_tree(costume_dat, joint_roots[0].data_offset)
    fighter_parts = parts[fighter_kind]
    joints: list[Joint | None] = []
    flat_to_part: dict[int, int] = {}
    source_index = 0
    for part_index in range(len(fighter_parts.joint_to_part)):
        if part_index in fighter_parts.optional_parts:
            joints.append(None)
            continue
        if source_index >= len(flat_joints):
            raise DatParseError(f"{costume_dat.context}: costume skeleton has fewer joints than fighter parts")
        flat_to_part[source_index] = part_index
        joints.append(flat_joints[source_index])
        source_index += 1
    if source_index != len(flat_joints):
        raise DatParseError(
            f"{costume_dat.context}: costume skeleton has {len(flat_joints)} joints but mapped {source_index}"
        )
    if special_bone >= len(joints) or joints[special_bone] is None:
        raise DatParseError(f"{fighter_dat.context}: invalid special bone {special_bone}")
    for part_index, joint in enumerate(joints):
        if joint is not None and joint.parent_index is not None:
            joints[part_index] = replace(joint, parent_index=flat_to_part[joint.parent_index])
    return FighterPoseSource(tuple(joints), parts, model_scale, special_bone)


def pose_matrices(
    source: FighterPoseSource,
    tree: FigaTree,
    *,
    fighter_kind: int,
    source_kind: int,
    additional_bones: int,
    raw_action_flags: int,
    animation_time: float,
    fighter_scale: float = 1.0,
    facing: int = 1,
) -> tuple[tuple[tuple[float, float, float, float], ...] | None, ...]:
    joints = list(source.joints)
    source_parts = source.parts[source_kind]
    target_parts = source.parts[fighter_kind]
    source_part_indexes = [
        index
        for index in range(len(source_parts.joint_to_part))
        if index not in source_parts.optional_parts or additional_bones & (1 << _optional_part_bit(source_parts, index))
    ]
    if len(tree.nodes) > len(source_part_indexes):
        raise DatParseError(
            f"FigaTree has {len(tree.nodes)} nodes for {len(source_part_indexes)} available source parts"
        )

    for node, source_part in zip(tree.nodes, source_part_indexes, strict=False):
        target_part = source_part
        if source_kind != fighter_kind:
            common_part = source_parts.joint_to_part[source_part]
            target_part = target_parts.part_to_joint[common_part] if common_part != 0xFF else 0xFF
        else:
            common_part = target_parts.joint_to_part[target_part]
        if target_part == 0xFF or target_part >= len(joints) or joints[target_part] is None or not node.tracks:
            continue
        joint = joints[target_part]
        assert joint is not None
        # DESNOTE(jbarber, 2026-09-06): Cross-fighter retargeting discards XYZ
        # tracks unless the target part has fighter part flag b3. These are the
        # common parts that carry that flag in the retail skeleton setup. See
        # https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/ftanim.c#L678-L689
        allow_translation = source_kind == fighter_kind or common_part in _FULL_TRANSLATION_PARTS
        rotation = joint.rotation
        scale = joint.scale
        translation = joint.translation
        for track in node.tracks:
            value = track.value_at(animation_time)
            if value is None:
                continue
            if track.track_type == 1:
                rotation = replace(rotation, x=value)
            elif track.track_type == 2:
                rotation = replace(rotation, y=value)
            elif track.track_type == 3:
                rotation = replace(rotation, z=value)
            elif track.track_type == 5 and allow_translation:
                translation = replace(translation, x=value)
            elif track.track_type == 6 and allow_translation:
                translation = replace(translation, y=value)
            elif track.track_type == 7 and allow_translation:
                translation = replace(translation, z=value)
            elif track.track_type == 8:
                scale = replace(scale, x=value)
            elif track.track_type == 9:
                scale = replace(scale, y=value)
            elif track.track_type == 10:
                scale = replace(scale, z=value)
        flags = joint.flags | _JOBJ_CLASSICAL_SCALING if tree.type & 1 else joint.flags & ~_JOBJ_CLASSICAL_SCALING
        joints[target_part] = replace(joint, flags=flags, rotation=rotation, scale=scale, translation=translation)

    root = joints[0]
    assert root is not None
    model_scale = source.model_scale * fighter_scale
    # DESNOTE(jbarber, 2026-09-06): Motion-state entry resets TopN to +/-90
    # degrees around Y, converting model-forward Z into gameplay X. See
    # https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/fighter.c#L1168-L1172.
    joints[0] = replace(
        root,
        rotation=Vec3(0.0, math.pi / 2 * facing, 0.0),
        scale=Vec3(model_scale, model_scale, model_scale),
    )
    special = joints[source.special_bone]
    assert special is not None
    inverse_model_scale = 1.0 / source.model_scale
    joints[source.special_bone] = replace(
        special,
        scale=Vec3(inverse_model_scale, inverse_model_scale, inverse_model_scale),
    )
    if raw_action_flags & _ANIMATION_ROOT_MOTION:
        trans_n = target_parts.part_to_joint[_PART_TRANS_N]
        if trans_n != 0xFF and trans_n < len(joints) and joints[trans_n] is not None:
            joint = joints[trans_n]
            assert joint is not None
            joints[trans_n] = replace(joint, translation=Vec3(0.0, 0.0, 0.0))

    matrices: list[tuple[tuple[float, float, float, float], ...] | None] = []
    accumulated_scales: list[Vec3 | None] = []
    for joint in joints:
        if joint is None:
            matrices.append(None)
            accumulated_scales.append(None)
            continue
        parent_matrix = None if joint.parent_index is None else matrices[joint.parent_index]
        parent_scale = None if joint.parent_index is None else accumulated_scales[joint.parent_index]
        local = _srt_matrix(joint.scale, joint.rotation, joint.translation, parent_scale)
        matrices.append(local if parent_matrix is None else _concat_matrix(parent_matrix, local))
        if joint.flags & _JOBJ_CLASSICAL_SCALING:
            accumulated_scales.append(parent_scale)
        else:
            accumulated_scales.append(joint.scale if parent_scale is None else _multiply_vec(joint.scale, parent_scale))
    return tuple(matrices)


def transform_point(
    matrix: tuple[tuple[float, float, float, float], ...],
    point: Vec3,
) -> Vec3:
    return Vec3(
        matrix[0][0] * point.x + matrix[0][1] * point.y + matrix[0][2] * point.z + matrix[0][3],
        matrix[1][0] * point.x + matrix[1][1] * point.y + matrix[1][2] * point.z + matrix[1][3],
        matrix[2][0] * point.x + matrix[2][1] * point.y + matrix[2][2] * point.z + matrix[2][3],
    )


def _decode_track(data: bytes, value_format: int, tangent_format: int, context: str) -> tuple[AnimationKey, ...]:
    offset = 0
    frame = 0
    keys: list[AnimationKey] = []
    while offset < len(data):
        packed, offset = _read_packed(data, offset, context)
        interpolation = packed & 0x0F
        count = (packed >> 4) + 1
        if interpolation == 0:
            break
        if interpolation not in range(1, 7):
            raise DatParseError(f"{context}: unsupported FOBJ interpolation opcode {interpolation}")
        for _ in range(count):
            if len(keys) >= _MAX_FOBJ_KEYS:
                raise DatParseError(f"{context}: FOBJ track exceeds {_MAX_FOBJ_KEYS} keys")
            value = None
            tangent = None
            wait = 0
            if interpolation in (1, 2, 3, 4, 6):
                value, offset = _read_fraction(data, offset, value_format, context)
            if interpolation in (4, 5):
                tangent, offset = _read_fraction(data, offset, tangent_format, context)
            if interpolation in (1, 2, 3, 4):
                wait, offset = _read_packed(data, offset, context)
            if interpolation in (1, 2, 3):
                tangent = 0.0
            keys.append(AnimationKey(frame, value, tangent, interpolation))
            frame += wait
    if offset != len(data):
        raise DatParseError(f"{context}: FOBJ track has {len(data) - offset} trailing bytes")
    return tuple(keys)


def _read_packed(data: bytes, offset: int, context: str) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise DatParseError(f"{context}: truncated packed FOBJ integer")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
        if shift > 28:
            raise DatParseError(f"{context}: oversized packed FOBJ integer")


def _read_fraction(data: bytes, offset: int, flag: int, context: str) -> tuple[float, int]:
    encoding = flag & 0xE0
    divisor = float(1 << (flag & 0x1F))
    formats = {0x00: ("<f", 4), 0x20: ("<h", 2), 0x40: ("<H", 2), 0x60: ("<b", 1), 0x80: ("<B", 1)}
    if encoding not in formats:
        raise DatParseError(f"{context}: invalid FOBJ fraction format 0x{flag:02X}")
    value_format, size = formats[encoding]
    if offset > len(data) - size:
        raise DatParseError(f"{context}: truncated FOBJ fraction")
    value = struct.unpack_from(value_format, data, offset)[0]
    return float(value) if encoding == 0 else float(value) / divisor, offset + size


def _parse_joint_tree(dat: HsdDat, root: int) -> tuple[Joint, ...]:
    joints: list[Joint] = []
    seen: set[int] = set()

    def visit_siblings(offset: int | None, parent: int | None) -> None:
        while offset is not None:
            if offset in seen:
                raise DatParseError(f"{dat.context}: JOBJ hierarchy has a cycle at data offset 0x{offset:X}")
            if len(joints) >= _MAX_FIGHTER_PARTS:
                raise DatParseError(f"{dat.context}: JOBJ hierarchy exceeds {_MAX_FIGHTER_PARTS} joints")
            seen.add(offset)
            dat.require_range(offset, 0x40, "JOBJ")
            flags = dat.u32(offset + 4)
            if flags & _JOBJ_INSTANCE:
                raise DatParseError(f"{dat.context}: fighter JOBJ instances are unsupported")
            child = dat.pointer(offset + 8, description="JOBJ child")
            sibling = dat.pointer(offset + 0x0C, description="JOBJ sibling")
            values = struct.unpack_from(">9f", dat.data, offset + 0x14)
            index = len(joints)
            joints.append(
                Joint(
                    parent,
                    flags,
                    Vec3(*values[0:3]),
                    Vec3(*values[3:6]),
                    Vec3(*values[6:9]),
                )
            )
            visit_siblings(child, index)
            offset = sibling

    visit_siblings(root, None)
    return tuple(joints)


def _optional_part_bit(parts: FighterParts, part: int) -> int:
    return parts.optional_parts.index(part)


def _float32(value: float) -> float:
    return struct.unpack(">f", struct.pack(">f", value))[0]


def _multiply_vec(left: Vec3, right: Vec3) -> Vec3:
    return Vec3(left.x * right.x, left.y * right.y, left.z * right.z)


def _srt_matrix(
    scale: Vec3,
    rotation: Vec3,
    translation: Vec3,
    parent_scale: Vec3 | None,
) -> tuple[tuple[float, float, float, float], ...]:
    sin_x, cos_x = math.sin(rotation.x), math.cos(rotation.x)
    sin_y, cos_y = math.sin(rotation.y), math.cos(rotation.y)
    sin_z, cos_z = math.sin(rotation.z), math.cos(rotation.z)
    scale_x0 = scale_x1 = scale_x2 = scale.x
    scale_y0 = scale_y1 = scale_y2 = scale.y
    scale_z0 = scale_z1 = scale_z2 = scale.z
    if parent_scale is not None:
        scale_y0 *= parent_scale.y / parent_scale.x
        scale_z0 *= parent_scale.z / parent_scale.x
        scale_x1 *= parent_scale.x / parent_scale.y
        scale_z1 *= parent_scale.z / parent_scale.y
        scale_x2 *= parent_scale.x / parent_scale.z
        scale_y2 *= parent_scale.y / parent_scale.z
    return (
        (
            cos_z * (scale_x0 * cos_y),
            scale_y0 * (cos_z * (sin_x * sin_y) - cos_x * sin_z),
            scale_z0 * (cos_z * (cos_x * sin_y) + sin_x * sin_z),
            translation.x,
        ),
        (
            sin_z * (scale_x1 * cos_y),
            scale_y1 * (sin_z * (sin_x * sin_y) + cos_x * cos_z),
            scale_z1 * (sin_z * (cos_x * sin_y) - sin_x * cos_z),
            translation.y,
        ),
        (
            -scale_x2 * sin_y,
            cos_y * (scale_y2 * sin_x),
            cos_y * (scale_z2 * cos_x),
            translation.z,
        ),
    )


def _concat_matrix(
    left: tuple[tuple[float, float, float, float], ...],
    right: tuple[tuple[float, float, float, float], ...],
) -> tuple[tuple[float, float, float, float], ...]:
    rows = []
    for row in range(3):
        rows.append(
            (
                *(
                    sum(left[row][index] * right[index][column] for index in range(3))
                    for column in range(3)
                ),
                sum(left[row][index] * right[index][3] for index in range(3)) + left[row][3],
            )
        )
    return tuple(rows)


__all__ = [
    "AnimationKey",
    "AnimationNode",
    "AnimationTrack",
    "FigaTree",
    "FighterParts",
    "FighterPoseSource",
    "Joint",
    "Vec3",
    "parse_figatree",
    "parse_fighter_parts",
    "parse_fighter_pose_source",
    "pose_matrices",
    "retail_fixed_point",
    "transform_point",
]
