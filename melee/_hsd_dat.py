"""Bounds-checked readers for the HSD DAT structures needed by framedata."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from typing import NoReturn


class DatParseError(ValueError):
    """Raised when an HSD DAT container or required object is malformed."""


@dataclass(frozen=True, slots=True)
class DatRoot:
    name: str
    data_offset: int
    is_reference: bool = False


@dataclass(frozen=True, slots=True)
class RawFighterAction:
    index: int
    symbol: str | None
    animation_offset: int
    animation_size: int
    script_data_offset: int | None
    flags: int
    runtime_animation_pointer: int


class HsdDat:
    """A validated HSD DAT held entirely in memory."""

    def __init__(self, data: bytes, *, context: str = "DAT"):
        self.context = context
        self._file = bytes(data)
        if len(self._file) < 0x20:
            self._fail(f"is shorter than the 0x20-byte header ({len(self._file)} bytes)")
        total_size, self.data_size, reloc_count, root_count, ref_count = struct.unpack_from(">IIIII", self._file)
        if total_size != len(self._file):
            self._fail(f"header size {total_size} does not match supplied size {len(self._file)}")
        if self.data_size > total_size - 0x20:
            self._fail(f"data size 0x{self.data_size:X} exceeds the file")
        if self.data_size % 4:
            self._fail(f"data size 0x{self.data_size:X} is not 4-byte aligned")
        self.version = self._file[0x14:0x18]
        self.data = self._file[0x20 : 0x20 + self.data_size]
        self._data_string_cache: dict[int, str] = {}
        self._data_string_bytes = 0
        reloc_start = 0x20 + self.data_size
        tables_size = reloc_count * 4 + (root_count + ref_count) * 8
        if tables_size > total_size - reloc_start:
            self._fail("relocation/root tables exceed the file")

        locations: set[int] = set()
        targets: set[int] = set()
        for index in range(reloc_count):
            location = struct.unpack_from(">I", self._file, reloc_start + index * 4)[0]
            if location % 4 or location > self.data_size - 4:
                self._fail(f"relocation {index} has invalid data offset 0x{location:X}")
            if location in locations:
                self._fail(f"duplicate relocation location 0x{location:X}")
            target = self.u32(location)
            if target >= self.data_size:
                self._fail(f"relocation at 0x{location:X} targets 0x{target:X} outside data")
            locations.add(location)
            targets.add(target)
        self.pointer_locations = frozenset(locations)

        roots_start = reloc_start + reloc_count * 4
        strings_start = roots_start + (root_count + ref_count) * 8
        self._name_cache: dict[int, str] = {}
        self._name_bytes = 0
        roots: list[DatRoot] = []
        for index in range(root_count):
            target, string_offset = struct.unpack_from(">II", self._file, roots_start + index * 8)
            if target >= self.data_size:
                self._fail(f"root {index} targets data offset 0x{target:X}")
            name = self._file_c_string(strings_start + string_offset, strings_start, f"root {index}")
            roots.append(DatRoot(name, target))
            targets.add(target)

        references: list[DatRoot] = []
        reference_locations: set[int] = set()
        for index in range(ref_count):
            entry_offset = roots_start + (root_count + index) * 8
            target, string_offset = struct.unpack_from(">II", self._file, entry_offset)
            name = self._file_c_string(strings_start + string_offset, strings_start, f"reference {index}")
            self._validate_reference_chain(target, index, reference_locations)
            references.append(DatRoot(name, target, True))
        self.roots = tuple(roots)
        self.references = tuple(references)
        self.object_offsets = tuple(sorted(targets | reference_locations | {self.data_size}))

    def _validate_reference_chain(self, offset: int, index: int, locations: set[int]) -> None:
        seen = set()
        while offset != 0xFFFFFFFF:
            if offset % 4 or offset > self.data_size - 4:
                self._fail(f"reference {index} has invalid link offset 0x{offset:X}")
            if offset in seen:
                self._fail(f"reference {index} has a cycle at data offset 0x{offset:X}")
            if offset in locations:
                self._fail(f"reference {index} reuses link offset 0x{offset:X}")
            seen.add(offset)
            locations.add(offset)
            offset = self.u32(offset)
            if offset == 0:
                break

    def _fail(self, message: str) -> NoReturn:
        raise DatParseError(f"{self.context}: {message}")

    def require_range(self, offset: int, size: int, description: str) -> None:
        if offset < 0 or size < 0 or offset > self.data_size or size > self.data_size - offset:
            self._fail(f"{description} range 0x{offset:X}+0x{size:X} exceeds data size 0x{self.data_size:X}")

    def u32(self, offset: int) -> int:
        self.require_range(offset, 4, "u32")
        return struct.unpack_from(">I", self.data, offset)[0]

    def pointer(self, offset: int, *, nullable: bool = True, description: str = "pointer") -> int | None:
        self.require_range(offset, 4, description)
        value = self.u32(offset)
        if offset in self.pointer_locations:
            if value >= self.data_size:
                self._fail(f"{description} at data offset 0x{offset:X} targets 0x{value:X}")
            return value
        if value == 0 and nullable:
            return None
        self._fail(f"{description} at data offset 0x{offset:X} is not relocated")

    def c_string(self, offset: int, description: str = "string") -> str:
        if offset < 0 or offset >= self.data_size:
            self._fail(f"{description} starts outside data at 0x{offset:X}")
        if offset in self._data_string_cache:
            return self._data_string_cache[offset]
        boundary = self.next_object_offset(offset)
        end = self.data.find(b"\0", offset, boundary)
        if end < 0:
            self._fail(
                f"{description} at data offset 0x{offset:X} is not NUL-terminated before object boundary 0x{boundary:X}"
            )
        byte_length = end - offset
        if byte_length > self.data_size - self._data_string_bytes:
            self._fail("aggregate data string bytes exceed the DAT data size")
        try:
            value = self.data[offset:end].decode("ascii")
        except UnicodeDecodeError as exc:
            raise DatParseError(f"{self.context}: {description} at data offset 0x{offset:X} is not ASCII") from exc
        self._data_string_bytes += byte_length
        self._data_string_cache[offset] = value
        return value

    def _file_c_string(self, offset: int, lower_bound: int, description: str) -> str:
        if offset < lower_bound or offset >= len(self._file):
            self._fail(f"{description} string offset is outside the string table")
        if offset in self._name_cache:
            return self._name_cache[offset]
        end = self._file.find(b"\0", offset)
        if end < 0:
            self._fail(f"{description} string is not NUL-terminated")
        byte_length = end - offset
        if byte_length > len(self._file) - self._name_bytes:
            self._fail("aggregate root/reference name bytes exceed the DAT size")
        try:
            name = self._file[offset:end].decode("ascii")
        except UnicodeDecodeError as exc:
            raise DatParseError(f"{self.context}: {description} string is not ASCII") from exc
        self._name_bytes += byte_length
        self._name_cache[offset] = name
        return name

    def next_object_offset(self, offset: int) -> int:
        for boundary in self.object_offsets:
            if boundary > offset:
                return boundary
        self._fail(f"no object boundary follows data offset 0x{offset:X}")

    def fighter_actions(
        self,
        *,
        expected_root: str | None = None,
        expected_count: int | None = None,
    ) -> tuple[RawFighterAction, ...]:
        roots = [root for root in self.roots if root.name.startswith("ftData")]
        if len(roots) != 1:
            self._fail(f"expected one ftData public root, found {len(roots)}")
        if expected_root is not None and roots[0].name != expected_root:
            self._fail(f"expected public root {expected_root!r}, found {roots[0].name!r}")
        fighter = roots[0].data_offset
        if fighter % 4:
            self._fail(f"fighter root has unaligned data offset 0x{fighter:X}")
        self.require_range(fighter, 0x60, "fighter root")
        actions = self.pointer(fighter + 0x0C, nullable=False, description="fighter action table")
        dynamic = self.pointer(fighter + 0x10, description="fighter dynamic behavior table")
        if actions is None:
            self._fail("fighter action table is null")
        if actions % 4:
            self._fail(f"fighter action table has unaligned data offset 0x{actions:X}")
        if self.next_object_offset(fighter) < fighter + 0x60:
            self._fail(f"fighter root at 0x{fighter:X} overlaps another object before its 0x60-byte extent")
        if expected_count is not None:
            if expected_count <= 0:
                self._fail(f"invalid expected fighter action count {expected_count}")
            boundary = actions + expected_count * 0x18
            self.require_range(actions, expected_count * 0x18, "fighter action table")
            if self.next_object_offset(actions) < boundary:
                self._fail("fighter action table overlaps another HSD object")
            if dynamic is None:
                self._fail("fighter dynamic behavior table is null")
            self.require_range(dynamic, expected_count * 2, "fighter dynamic behavior table")
            if self.next_object_offset(dynamic) < dynamic + expected_count * 2:
                self._fail("fighter dynamic behavior table overlaps another HSD object")
        else:
            boundary = dynamic if dynamic is not None and dynamic > actions else self.next_object_offset(actions)
        if boundary <= actions or (boundary - actions) % 0x18:
            self._fail(f"action table 0x{actions:X}..0x{boundary:X} is not a whole number of 0x18-byte entries")

        result = []
        for index, offset in enumerate(range(actions, boundary, 0x18)):
            symbol_pointer = self.pointer(offset, description=f"action {index} symbol")
            symbol = self.c_string(symbol_pointer, f"action {index} symbol") if symbol_pointer is not None else None
            animation_offset, animation_size = struct.unpack_from(">II", self.data, offset + 4)
            script = self.pointer(offset + 0x0C, description=f"action {index} script")
            flags, runtime_pointer = struct.unpack_from(">II", self.data, offset + 0x10)
            result.append(
                RawFighterAction(
                    index,
                    symbol,
                    animation_offset,
                    animation_size,
                    script,
                    flags,
                    runtime_pointer,
                )
            )
        return tuple(result)


def parse_figatree_frame_count(
    data: bytes,
    *,
    expected_root: str | None = None,
    context: str = "animation DAT",
) -> float:
    """Parse the floating-point frame count from an embedded ``_figatree`` DAT."""

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
    if root % 4:
        raise DatParseError(f"{context}: FigaTree root has unaligned data offset 0x{root:X}")
    dat.require_range(root, 0x14, "FigaTree")
    if dat.next_object_offset(root) < root + 0x14:
        raise DatParseError(f"{context}: FigaTree root overlaps another object before its 0x14-byte extent")
    frame_count = struct.unpack_from(">f", dat.data, root + 8)[0]
    if not math.isfinite(frame_count) or frame_count < 0:
        raise DatParseError(f"{context}: invalid FigaTree frame count {frame_count!r}")
    return frame_count


__all__ = ["DatParseError", "DatRoot", "HsdDat", "RawFighterAction", "parse_figatree_frame_count"]
