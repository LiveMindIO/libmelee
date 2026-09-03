"""Lossless parsing and guarded interpretation of fighter subaction scripts."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, replace
from enum import Enum, IntEnum


class SubactionParseError(ValueError):
    """Raised when a subaction command stream is malformed or unsafe to run."""


class HurtScope(Enum):
    """The collision-state target selected by a hurt-state command."""

    BODY = "body"
    ALL_BONES = "all_bones"
    BONE = "bone"


class HurtState(IntEnum):
    """Known body collision states. Raw event values are retained as integers."""

    NORMAL = 0
    INVULNERABLE = 1
    INTANGIBLE = 2


class HitboxChange(Enum):
    CREATE = "create"
    DAMAGE = "damage"
    SIZE = "size"
    INTERACTION = "interaction"
    REMOVE = "remove"
    CLEAR = "clear"


@dataclass(frozen=True, slots=True)
class RawCommand:
    """One losslessly retained command at its original DAT location."""

    opcode: int
    data_offset: int
    dat_offset: int
    raw_words: tuple[int, ...]
    decoded: tuple[tuple[str, int | float | bool], ...] = ()

    def parameter(self, name: str) -> int | float | bool:
        """Return a decoded parameter without exposing a mutable mapping."""

        for key, value in self.decoded:
            if key == name:
                return value
        raise KeyError(name)


@dataclass(frozen=True, slots=True)
class ExecutedCommand:
    command: RawCommand
    order: int
    animation_time: float
    local_frame: int


@dataclass(frozen=True, slots=True)
class Hitbox:
    """A fighter hitbox whose XYZ geometry is bone-local, not world geometry."""

    hitbox_id: int
    hit_group: int
    bugged_only_hit_grabbed_fighter_flag: bool
    bone_id: int
    use_common_bone_ids: bool
    damage: int
    size: float
    bone_local_x: float
    bone_local_y: float
    bone_local_z: float
    angle: int
    knockback_growth: int
    weight_set_knockback: int
    item_hit_interaction: bool
    requires_thrown_hitbox_owner: bool
    ignore_fighter_scale: bool
    clank: bool
    rebound: bool
    base_knockback: int
    element: int
    shield_damage: int
    hit_sfx_severity: int
    hit_sfx_kind: int
    hits_grounded: bool
    hits_aerial: bool
    fighter_interaction: bool = True
    non_fighter_interaction: bool = True


@dataclass(frozen=True, slots=True)
class HitboxEvent:
    change: HitboxChange
    order: int
    animation_time: float
    local_frame: int
    command: RawCommand
    hitbox_id: int | None
    hitbox: Hitbox | None
    raw_value: int | None = None
    interaction_type: int | None = None


@dataclass(frozen=True, slots=True)
class HitboxGeneration:
    generation: int
    hitbox_id: int
    start_time: float
    start_frame: int
    end_time: float
    end_frame: int
    initial_hitbox: Hitbox
    final_hitbox: Hitbox
    events: tuple[HitboxEvent, ...]


@dataclass(frozen=True, slots=True)
class ThrowEvent:
    order: int
    animation_time: float
    local_frame: int
    command: RawCommand
    throw_type: int
    damage: int
    angle: int
    knockback_growth: int
    weight_set_knockback: int
    base_knockback: int
    element: int
    hit_sfx_severity: int
    hit_sfx_kind: int


@dataclass(frozen=True, slots=True)
class HurtStateEvent:
    order: int
    animation_time: float
    local_frame: int
    command: RawCommand
    scope: HurtScope
    state: int
    bone_id: int | None = None


@dataclass(frozen=True, slots=True)
class FrameSnapshot:
    """One-indexed script state; conditional hitboxes may require runtime context."""

    local_frame: int
    animation_time: float
    active_hitboxes: tuple[Hitbox, ...]
    interrupt_allowed: bool


@dataclass(frozen=True, slots=True)
class ActionTimeline:
    commands: tuple[ExecutedCommand, ...]
    hitbox_events: tuple[HitboxEvent, ...]
    hitbox_generations: tuple[HitboxGeneration, ...]
    throw_events: tuple[ThrowEvent, ...]
    hurt_state_events: tuple[HurtStateEvent, ...]
    iasa_time: float | None
    iasa_frame: int | None
    frames: tuple[FrameSnapshot, ...]
    animation_timer_encountered: bool
    script_loop_encountered: bool
    frame_guard_encountered: bool

    @property
    def first_frame(self) -> int:
        """The invariant first public frame number for every action timeline."""

        return 1

    @property
    def frame_count(self) -> int:
        """Number of one-indexed frame snapshots in this timeline."""

        return len(self.frames)

    def frame(self, local_frame: int) -> FrameSnapshot:
        """Return a frame by libmelee's one-based action-frame convention."""

        if local_frame < 1 or local_frame > len(self.frames):
            valid = f"1..{len(self.frames)}" if self.frames else "empty"
            raise IndexError(f"local frames are one-indexed; valid range is {valid}, got {local_frame}")
        return self.frames[local_frame - 1]


# Number of 32-bit words consumed by opcodes 10 through 58 in NTSC 1.02.
_FIGHTER_LENGTHS = (
    5,
    5,
    1,
    1,
    1,
    1,
    1,
    3,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    3,
    1,
    1,
    1,
    7,
    4,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    3,
    3,
    2,
    1,
    4,
)
_COMMAND_LENGTHS = {opcode: 1 for opcode in range(10)}
_COMMAND_LENGTHS.update({5: 2, 7: 2})
_COMMAND_LENGTHS.update({opcode: length for opcode, length in enumerate(_FIGHTER_LENGTHS, 10)})


def _signed(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return value - (1 << bits) if value & sign else value


def _fields(words: tuple[int, ...], specifications: tuple[tuple[str, int, bool], ...]) -> dict[str, int]:
    packed = int.from_bytes(b"".join(word.to_bytes(4, "big") for word in words), "big")
    total_bits = len(words) * 32
    position = 6
    result = {}
    for name, width, signed in specifications:
        if position + width > total_bits:
            raise SubactionParseError(f"decoded field {name!r} exceeds a {len(words)}-word command")
        shift = total_bits - position - width
        value = (packed >> shift) & ((1 << width) - 1)
        result[name] = _signed(value, width) if signed else value
        position += width
    return result


def _frame(time: float) -> int:
    return max(1, math.ceil(time))


def _animation_snapshot_count(frame_count: float) -> int:
    if frame_count <= 0:
        return 0
    return max(1, math.ceil(frame_count) - 1)


def _decode_command(opcode: int, words: tuple[int, ...]) -> tuple[tuple[str, int | float | bool], ...]:
    specs: tuple[tuple[str, int, bool], ...] = ()
    if opcode in (1, 2):
        specs = (("frame", 26, False),)
    elif opcode == 3:
        specs = (("count", 26, False),)
    elif opcode in (5, 7):
        specs = (("target_tag", 26, False), ("target", 32, False))
    elif opcode == 8:
        specs = (("raw_timer", 26, False),)
    elif opcode == 9:
        specs = (("param_1", 8, False), ("param_2", 18, False))
    elif opcode == 11:
        specs = (
            ("hitbox_id", 3, False),
            ("hit_group", 3, False),
            ("bugged_only_hit_grabbed_fighter_flag", 1, False),
            ("bone_id", 8, False),
            ("use_common_bone_ids", 1, False),
            ("damage", 10, False),
            ("size_raw", 16, False),
            ("bone_local_z_raw", 16, True),
            ("bone_local_y_raw", 16, True),
            ("bone_local_x_raw", 16, True),
            ("angle", 9, False),
            ("knockback_growth", 9, False),
            ("weight_set_knockback", 9, False),
            ("item_hit_interaction", 1, False),
            ("requires_thrown_hitbox_owner", 1, False),
            ("ignore_fighter_scale", 1, False),
            ("clank", 1, False),
            ("rebound", 1, False),
            ("base_knockback", 9, False),
            ("element", 5, False),
            ("shield_damage", 8, True),
            ("hit_sfx_severity", 3, False),
            ("hit_sfx_kind", 5, False),
            ("hits_grounded", 1, False),
            ("hits_aerial", 1, False),
        )
    elif opcode in (12, 13):
        specs = (("hitbox_id", 3, False), ("value", 23, False))
    elif opcode == 14:
        specs = (("hitbox_id", 24, False), ("interaction_type", 1, False), ("value", 1, False))
    elif opcode in (15, 26, 27):
        specs = (("value", 26, False),)
    elif opcode == 28:
        specs = (("bone_id", 8, False), ("state", 18, False))
    elif opcode == 34:
        specs = (
            ("throw_type", 3, False),
            ("damage", 23, False),
            ("angle", 9, False),
            ("knockback_growth", 9, False),
            ("weight_set_knockback", 9, False),
            ("unused_1", 5, False),
            ("base_knockback", 9, False),
            ("element", 4, False),
            ("hit_sfx_severity", 3, False),
            ("hit_sfx_kind", 4, False),
            ("unused_2", 12, False),
        )
    values: dict[str, int | float | bool] = {}
    if specs:
        values.update(_fields(words, specs))
    if opcode == 11:
        values["size"] = values["size_raw"] / 256.0
        values["bone_local_x"] = values["bone_local_z_raw"] / 256.0
        values["bone_local_y"] = values["bone_local_y_raw"] / 256.0
        values["bone_local_z"] = values["bone_local_x_raw"] / 256.0
    elif opcode == 13:
        values["size"] = values["value"] / 256.0
    return tuple(values.items())


def _hitbox(command: RawCommand) -> Hitbox:
    values = dict(command.decoded)
    return Hitbox(
        hitbox_id=int(values["hitbox_id"]),
        hit_group=int(values["hit_group"]),
        bugged_only_hit_grabbed_fighter_flag=bool(values["bugged_only_hit_grabbed_fighter_flag"]),
        bone_id=int(values["bone_id"]),
        use_common_bone_ids=bool(values["use_common_bone_ids"]),
        damage=int(values["damage"]),
        size=float(values["size"]),
        bone_local_x=float(values["bone_local_x"]),
        bone_local_y=float(values["bone_local_y"]),
        bone_local_z=float(values["bone_local_z"]),
        angle=int(values["angle"]),
        knockback_growth=int(values["knockback_growth"]),
        weight_set_knockback=int(values["weight_set_knockback"]),
        item_hit_interaction=bool(values["item_hit_interaction"]),
        requires_thrown_hitbox_owner=bool(values["requires_thrown_hitbox_owner"]),
        ignore_fighter_scale=bool(values["ignore_fighter_scale"]),
        clank=bool(values["clank"]),
        rebound=bool(values["rebound"]),
        base_knockback=int(values["base_knockback"]),
        element=int(values["element"]),
        shield_damage=int(values["shield_damage"]),
        hit_sfx_severity=int(values["hit_sfx_severity"]),
        hit_sfx_kind=int(values["hit_sfx_kind"]),
        hits_grounded=bool(values["hits_grounded"]),
        hits_aerial=bool(values["hits_aerial"]),
        fighter_interaction=True,
        non_fighter_interaction=True,
    )


def interpret_subaction(
    data: bytes,
    script_data_offset: int,
    *,
    pointer_locations: frozenset[int] = frozenset(),
    animation_frame_count: float | None = None,
    context: str = "subaction",
    max_commands: int = 100_000,
    max_call_depth: int = 64,
    max_loop_depth: int = 64,
    max_frames: int = 10_000,
    truncate_at_max_frames: bool = False,
) -> ActionTimeline:
    """Interpret a fighter script while retaining every reached command word."""

    if script_data_offset < 0 or script_data_offset >= len(data) or script_data_offset % 4:
        raise SubactionParseError(f"{context}: invalid script data offset 0x{script_data_offset:X}")
    if animation_frame_count is not None and (
        not math.isfinite(animation_frame_count) or animation_frame_count < 0 or animation_frame_count > max_frames
    ):
        raise SubactionParseError(f"{context}: invalid animation frame count {animation_frame_count!r}")
    if max_commands <= 0 or max_call_depth <= 0 or max_loop_depth <= 0 or max_frames <= 0:
        raise SubactionParseError(f"{context}: command, call, loop, and frame guards must be positive")

    pc = script_data_offset
    time = 0.0
    timer = 0.0
    calls: list[int] = []
    loops: list[list[int]] = []
    executed: list[ExecutedCommand] = []
    hitbox_events: list[HitboxEvent] = []
    throw_events: list[ThrowEvent] = []
    hurt_events: list[HurtStateEvent] = []
    iasa_time: float | None = None
    animation_timer = False
    script_loop = False
    frame_guard = False
    seen: set[tuple[int, float, float, tuple[int, ...], tuple[tuple[int, int], ...]]] = set()
    seen_control_flow: set[tuple[int, tuple[int, ...], tuple[tuple[int, int], ...]]] = set()

    while True:
        if len(executed) >= max_commands:
            raise SubactionParseError(f"{context}: command guard exceeded {max_commands} executions")
        state = (pc, time, timer, tuple(calls), tuple((loop[0], loop[1]) for loop in loops))
        if state in seen:
            raise SubactionParseError(f"{context}: control-flow cycle at data offset 0x{pc:X}, time {time:g}")
        seen.add(state)
        seen_control_flow.add((pc, tuple(calls), tuple((loop[0], loop[1]) for loop in loops)))
        if pc % 4 or pc < 0 or pc > len(data) - 4:
            raise SubactionParseError(f"{context}: command at data offset 0x{pc:X} is outside DAT data")
        first = struct.unpack_from(">I", data, pc)[0]
        opcode = first >> 26
        length = _COMMAND_LENGTHS.get(opcode)
        if length is None:
            raise SubactionParseError(f"{context}: unsupported opcode {opcode} at DAT offset 0x{pc + 0x20:X}")
        byte_length = length * 4
        if byte_length > len(data) - pc:
            raise SubactionParseError(
                f"{context}: opcode {opcode} at DAT offset 0x{pc + 0x20:X} is truncated; needs {length} words"
            )
        words = struct.unpack_from(f">{length}I", data, pc)
        command = RawCommand(opcode, pc, pc + 0x20, words, _decode_command(opcode, words))
        order = len(executed)
        local_frame = _frame(time)
        executed.append(ExecutedCommand(command, order, time, local_frame))

        if opcode == 0:
            break
        if opcode in (1, 2):
            frame = float(command.parameter("frame"))
            timer = timer + frame if opcode == 1 else frame - time
            if timer > 0:
                next_time = time + timer
                if _frame(next_time) > max_frames:
                    if not truncate_at_max_frames:
                        raise SubactionParseError(f"{context}: frame guard exceeded {max_frames} frames")
                    time = float(max_frames)
                    frame_guard = True
                    break
                time = next_time
                timer = 0.0
            pc += 4
            continue
        if opcode == 3:
            count = int(command.parameter("count"))
            if count <= 0:
                raise SubactionParseError(f"{context}: loop at DAT offset 0x{pc + 0x20:X} has zero count")
            if len(loops) >= max_loop_depth:
                raise SubactionParseError(f"{context}: loop depth guard exceeded {max_loop_depth}")
            loops.append([pc + 4, count])
            pc += 4
            continue
        if opcode == 4:
            if not loops:
                raise SubactionParseError(f"{context}: execute-loop at DAT offset 0x{pc + 0x20:X} has no loop")
            loops[-1][1] -= 1
            if loops[-1][1] > 0:
                pc = loops[-1][0]
            else:
                loops.pop()
                pc += 4
            continue
        if opcode in (5, 7):
            if pc + 4 not in pointer_locations:
                raise SubactionParseError(
                    f"{context}: opcode {opcode} target at DAT offset 0x{pc + 0x24:X} is not relocated"
                )
            target = int(command.parameter("target"))
            if target % 4 or target < 0 or target >= len(data):
                raise SubactionParseError(f"{context}: opcode {opcode} targets invalid data offset 0x{target:X}")
            target_state = (target, tuple(calls), tuple((loop[0], loop[1]) for loop in loops))
            if opcode == 7 and target_state in seen_control_flow:
                script_loop = True
                break
            if opcode == 5:
                if len(calls) >= max_call_depth:
                    raise SubactionParseError(f"{context}: call depth guard exceeded {max_call_depth}")
                calls.append(pc + 8)
            pc = target
            continue
        if opcode == 6:
            if not calls:
                raise SubactionParseError(f"{context}: return at DAT offset 0x{pc + 0x20:X} has no caller")
            pc = calls.pop()
            continue
        if opcode == 8:
            animation_timer = True
            break

        _validate_runtime_indices(command, context)
        event = ExecutedCommand(command, order, time, local_frame)
        _append_combat_event(event, hitbox_events, throw_events, hurt_events)
        if opcode == 23 and iasa_time is None:
            iasa_time = time
        pc += byte_length

    generations = _build_generations(hitbox_events, max(time, animation_frame_count or 0.0))
    frames = _build_frames(hitbox_events, iasa_time, animation_frame_count, time)
    return ActionTimeline(
        tuple(executed),
        tuple(hitbox_events),
        generations,
        tuple(throw_events),
        tuple(hurt_events),
        iasa_time,
        _frame(iasa_time) if iasa_time is not None else None,
        frames,
        animation_timer,
        script_loop,
        frame_guard,
    )


def _validate_runtime_indices(command: RawCommand, context: str) -> None:
    values = dict(command.decoded)
    if command.opcode in (11, 12, 13, 14):
        hitbox_id = int(values["hitbox_id"])
    elif command.opcode == 15:
        hitbox_id = int(values["value"])
    else:
        hitbox_id = None
    if hitbox_id is not None and hitbox_id > 3:
        raise SubactionParseError(
            f"{context}: opcode {command.opcode} has invalid fighter hitbox ID {hitbox_id} "
            f"at DAT offset 0x{command.dat_offset:X}"
        )
    if command.opcode == 34 and int(values["throw_type"]) > 1:
        raise SubactionParseError(
            f"{context}: throw has invalid type {values['throw_type']} at DAT offset 0x{command.dat_offset:X}"
        )


def _append_combat_event(
    event: ExecutedCommand,
    hitboxes: list[HitboxEvent],
    throws: list[ThrowEvent],
    hurts: list[HurtStateEvent],
) -> None:
    command = event.command
    opcode = command.opcode
    values = dict(command.decoded)
    if opcode == 11:
        hitbox = _hitbox(command)
        hitboxes.append(
            HitboxEvent(
                HitboxChange.CREATE,
                event.order,
                event.animation_time,
                event.local_frame,
                command,
                hitbox.hitbox_id,
                hitbox,
            )
        )
    elif opcode in (12, 13):
        change = HitboxChange.DAMAGE if opcode == 12 else HitboxChange.SIZE
        hitboxes.append(
            HitboxEvent(
                change,
                event.order,
                event.animation_time,
                event.local_frame,
                command,
                int(values["hitbox_id"]),
                None,
                int(values["value"]),
            )
        )
    elif opcode == 14:
        hitboxes.append(
            HitboxEvent(
                HitboxChange.INTERACTION,
                event.order,
                event.animation_time,
                event.local_frame,
                command,
                int(values["hitbox_id"]),
                None,
                int(values["value"]),
                int(values["interaction_type"]),
            )
        )
    elif opcode == 15:
        hitboxes.append(
            HitboxEvent(
                HitboxChange.REMOVE,
                event.order,
                event.animation_time,
                event.local_frame,
                command,
                int(values["value"]),
                None,
            )
        )
    elif opcode == 16:
        hitboxes.append(
            HitboxEvent(
                HitboxChange.CLEAR,
                event.order,
                event.animation_time,
                event.local_frame,
                command,
                None,
                None,
            )
        )
    elif opcode in (26, 27, 28):
        if opcode == 26:
            scope, state, bone = HurtScope.BODY, int(values["value"]), None
        elif opcode == 27:
            scope, state, bone = HurtScope.ALL_BONES, int(values["value"]), None
        else:
            scope, state, bone = HurtScope.BONE, int(values["state"]), int(values["bone_id"])
        hurts.append(HurtStateEvent(event.order, event.animation_time, event.local_frame, command, scope, state, bone))
    elif opcode == 34:
        throws.append(
            ThrowEvent(
                event.order,
                event.animation_time,
                event.local_frame,
                command,
                int(values["throw_type"]),
                int(values["damage"]),
                int(values["angle"]),
                int(values["knockback_growth"]),
                int(values["weight_set_knockback"]),
                int(values["base_knockback"]),
                int(values["element"]),
                int(values["hit_sfx_severity"]),
                int(values["hit_sfx_kind"]),
            )
        )


def _build_generations(events: list[HitboxEvent], end_time: float) -> tuple[HitboxGeneration, ...]:
    # Active entries contain generation number, initial/current hitbox, and events.
    active: dict[int, tuple[int, Hitbox, Hitbox, list[HitboxEvent], float, int]] = {}
    counts: dict[int, int] = {}
    complete: list[HitboxGeneration] = []

    def close(hitbox_id: int, time: float, frame: int) -> None:
        item = active.pop(hitbox_id, None)
        if item is None:
            return
        generation, initial, current, changes, start_time, start_frame = item
        complete.append(
            HitboxGeneration(
                generation,
                hitbox_id,
                start_time,
                start_frame,
                time,
                frame,
                initial,
                current,
                tuple(changes),
            )
        )

    for event in events:
        if event.change is HitboxChange.CREATE and event.hitbox is not None and event.hitbox_id is not None:
            close(event.hitbox_id, event.animation_time, event.local_frame)
            generation = counts.get(event.hitbox_id, 0) + 1
            counts[event.hitbox_id] = generation
            active[event.hitbox_id] = (
                generation,
                event.hitbox,
                event.hitbox,
                [event],
                event.animation_time,
                event.local_frame,
            )
        elif event.change is HitboxChange.CLEAR:
            for hitbox_id in tuple(active):
                close(hitbox_id, event.animation_time, event.local_frame)
        elif event.hitbox_id is not None and event.change is HitboxChange.REMOVE:
            close(event.hitbox_id, event.animation_time, event.local_frame)
        elif event.hitbox_id is not None and event.hitbox_id in active:
            generation, initial, current, changes, start_time, start_frame = active[event.hitbox_id]
            if event.change is HitboxChange.DAMAGE and event.raw_value is not None:
                current = replace(current, damage=event.raw_value)
            elif event.change is HitboxChange.SIZE and event.raw_value is not None:
                current = replace(current, size=event.raw_value / 256.0)
            elif event.change is HitboxChange.INTERACTION and event.raw_value is not None:
                field = "fighter_interaction" if event.interaction_type == 0 else "non_fighter_interaction"
                current = replace(current, **{field: bool(event.raw_value)})
            changes.append(replace(event, hitbox=current))
            active[event.hitbox_id] = (generation, initial, current, changes, start_time, start_frame)
    for hitbox_id in tuple(active):
        close(hitbox_id, end_time, _frame(end_time))
    complete.sort(key=lambda generation: (generation.start_time, generation.events[0].order))
    return tuple(complete)


def _build_frames(
    events: list[HitboxEvent],
    iasa_time: float | None,
    animation_frame_count: float | None,
    final_time: float,
) -> tuple[FrameSnapshot, ...]:
    frame_count = (
        _animation_snapshot_count(animation_frame_count) if animation_frame_count is not None else _frame(final_time)
    )
    active: dict[int, Hitbox] = {}
    event_index = 0
    result = []
    for local_frame in range(1, frame_count + 1):
        animation_time = float(local_frame - 1)
        while event_index < len(events) and events[event_index].local_frame <= local_frame:
            event = events[event_index]
            if event.change is HitboxChange.CREATE and event.hitbox_id is not None and event.hitbox is not None:
                active[event.hitbox_id] = event.hitbox
            elif event.change is HitboxChange.CLEAR:
                active.clear()
            elif event.change is HitboxChange.REMOVE and event.hitbox_id is not None:
                active.pop(event.hitbox_id, None)
            elif event.hitbox_id is not None and event.hitbox_id in active:
                current = active[event.hitbox_id]
                if event.change is HitboxChange.DAMAGE and event.raw_value is not None:
                    active[event.hitbox_id] = replace(current, damage=event.raw_value)
                elif event.change is HitboxChange.SIZE and event.raw_value is not None:
                    active[event.hitbox_id] = replace(current, size=event.raw_value / 256.0)
                elif event.change is HitboxChange.INTERACTION and event.raw_value is not None:
                    field = "fighter_interaction" if event.interaction_type == 0 else "non_fighter_interaction"
                    active[event.hitbox_id] = replace(current, **{field: bool(event.raw_value)})
            event_index += 1
        result.append(
            FrameSnapshot(
                local_frame,
                animation_time,
                tuple(active[key] for key in sorted(active)),
                iasa_time is not None and _frame(iasa_time) <= local_frame,
            )
        )
    return tuple(result)


__all__ = [
    "ActionTimeline",
    "ExecutedCommand",
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
    "interpret_subaction",
]
