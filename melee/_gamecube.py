"""Minimal, read-only support for the GameCube disc filesystem."""

from __future__ import annotations

import os
import re
import stat
import struct
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType


class DiscImageError(ValueError):
    """Raised when a disc image is unsupported or structurally invalid."""


@dataclass(frozen=True, slots=True)
class FstEntry:
    """An immutable file or directory entry from a GameCube FST."""

    index: int
    name: str
    path: str
    is_directory: bool
    offset: int
    size: int
    parent_index: int | None


class GameCubeDisc:
    """Validate and provide bounded reads from an NTSC 1.02 Melee ISO."""

    _FIGHTER_RE = re.compile(r"^Pl([A-Za-z0-9]{2})\.dat$")

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        try:
            mode = self.path.stat().st_mode
        except OSError as exc:
            raise DiscImageError(f"cannot stat disc image {self.path!s}: {exc}") from exc
        if not stat.S_ISREG(mode):
            raise DiscImageError(f"disc image is not a regular file: {self.path!s}")

        self.size = self.path.stat().st_size
        if self.size < 0x430:
            raise DiscImageError(f"disc image is too small for a GameCube header: {self.size} bytes")
        with self.path.open("rb") as stream:
            header = stream.read(0x430)
            if len(header) != 0x430:
                raise DiscImageError("could not read the complete GameCube disc header")
            if header[0:6] != b"GALE01":
                raise DiscImageError(f"unsupported disc ID {header[0:6]!r}; expected b'GALE01'")
            if header[6] != 0:
                raise DiscImageError(f"unsupported disc number {header[6]}; expected disc 0")
            if header[7] != 2:
                raise DiscImageError(f"unsupported GALE01 revision {header[7]}; expected NTSC 1.02 revision 2")
            self.fst_offset, self.fst_size, fst_max_size = struct.unpack_from(">III", header, 0x424)
            if self.fst_size < 12 or self.fst_offset > self.size or self.fst_size > self.size - self.fst_offset:
                raise DiscImageError(
                    f"FST range 0x{self.fst_offset:X}+0x{self.fst_size:X} is outside the {self.size}-byte disc"
                )
            if self.fst_size > fst_max_size:
                raise DiscImageError(
                    f"FST size 0x{self.fst_size:X} exceeds the header maximum 0x{fst_max_size:X}"
                )
            stream.seek(self.fst_offset)
            fst = stream.read(self.fst_size)
        if len(fst) != self.fst_size:
            raise DiscImageError("could not read the complete FST")

        self.entries = self._parse_fst(fst)
        by_path = {entry.path: entry for entry in self.entries}
        if len(by_path) != len(self.entries):
            raise DiscImageError("FST contains duplicate paths")
        self.entries_by_path: Mapping[str, FstEntry] = MappingProxyType(by_path)
        self.fighter_members = self._pair_fighter_members()

    def _parse_fst(self, fst: bytes) -> tuple[FstEntry, ...]:
        root0, root1, count = struct.unpack_from(">III", fst)
        if root0 >> 24 != 1 or (root0 & 0xFFFFFF) != 0 or root1 != 0:
            raise DiscImageError("FST root entry is not a valid root directory")
        if count < 1 or count > len(fst) // 12:
            raise DiscImageError(f"invalid FST entry count {count}")
        strings_start = count * 12
        entries = [FstEntry(0, "", "", True, 0, count, None)]
        # Stack items are (directory index, exclusive ending entry, path).
        stack: list[tuple[int, int, str]] = [(0, count, "")]

        for index in range(1, count):
            while stack and index >= stack[-1][1]:
                stack.pop()
            if not stack:
                raise DiscImageError(f"FST entry {index} is outside the root directory")
            word0, word1, word2 = struct.unpack_from(">III", fst, index * 12)
            is_directory = bool(word0 >> 24)
            if word0 >> 24 not in (0, 1):
                raise DiscImageError(f"FST entry {index} has invalid directory marker 0x{word0 >> 24:02X}")
            name_offset = word0 & 0xFFFFFF
            name = self._fst_string(fst, strings_start, name_offset, index)
            if not name or not name.isprintable() or "/" in name or "\\" in name or name in (".", ".."):
                raise DiscImageError(f"FST entry {index} has unsafe name {name!r}")
            parent_index, parent_end, parent_path = stack[-1]
            path = f"{parent_path}/{name}" if parent_path else name

            if is_directory:
                if word1 != parent_index:
                    raise DiscImageError(f"FST directory {path!r} names parent {word1}, expected {parent_index}")
                if word2 <= index or word2 > parent_end:
                    raise DiscImageError(f"FST directory {path!r} has invalid next index {word2}")
                entry = FstEntry(index, name, path, True, 0, word2, parent_index)
                stack.append((index, word2, path))
            else:
                if word1 > self.size or word2 > self.size - word1:
                    raise DiscImageError(f"FST file {path!r} range 0x{word1:X}+0x{word2:X} is outside the disc")
                entry = FstEntry(index, name, path, False, word1, word2, parent_index)
            entries.append(entry)
        return tuple(entries)

    @staticmethod
    def _fst_string(fst: bytes, start: int, offset: int, index: int) -> str:
        position = start + offset
        if position < start or position >= len(fst):
            raise DiscImageError(f"FST entry {index} name offset 0x{offset:X} is outside the string table")
        end = fst.find(b"\0", position)
        if end < 0:
            raise DiscImageError(f"FST entry {index} name is not NUL-terminated")
        try:
            return fst[position:end].decode("ascii")
        except UnicodeDecodeError as exc:
            raise DiscImageError(f"FST entry {index} name is not ASCII") from exc

    def _pair_fighter_members(self) -> Mapping[str, tuple[FstEntry, FstEntry]]:
        base: dict[tuple[int | None, str], FstEntry] = {}
        animations: dict[tuple[int | None, str], FstEntry] = {}
        for entry in self.entries:
            if entry.is_directory:
                continue
            match = self._FIGHTER_RE.fullmatch(entry.name)
            if match and entry.name != "PlCo.dat":
                code = match.group(1)
                base[(entry.parent_index, code)] = entry
                continue
            if len(entry.name) == 10 and entry.name.startswith("Pl") and entry.name.endswith("AJ.dat"):
                code = entry.name[2:4]
                animations[(entry.parent_index, code)] = entry

        pairs: dict[str, tuple[FstEntry, FstEntry]] = {}
        for key, entry in base.items():
            animation = animations.get(key)
            if animation is None:
                continue
            code = key[1]
            if code in pairs:
                raise DiscImageError(f"multiple complete fighter DAT/AJ pairs found for code {code!r}")
            pairs[code] = (entry, animation)
        return MappingProxyType(pairs)

    def read_member(self, member: FstEntry | str) -> bytes:
        """Read exactly one validated FST member without extracting it."""

        entry = self.entries_by_path.get(member) if isinstance(member, str) else member
        if entry is None or entry.is_directory or entry not in self.entries:
            raise DiscImageError(f"not a file member of this disc: {member!r}")
        with self.path.open("rb") as stream:
            stream.seek(entry.offset)
            data = stream.read(entry.size)
        if len(data) != entry.size:
            raise DiscImageError(f"short read for disc member {entry.path!r}")
        return data


__all__ = ["DiscImageError", "FstEntry", "GameCubeDisc"]
