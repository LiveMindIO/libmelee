"""Audited executable metadata for the GALE01 NTSC 1.02 build."""

from dataclasses import dataclass
from types import MappingProxyType

DOLDECOMP_REVISION = "d15c9cffe939611627b3a7a77a446705d2998f5f"
DOLDECOMP_SOURCE = f"https://github.com/doldecomp/melee/commit/{DOLDECOMP_REVISION}"

COMMON_MOTION_STATE_TABLE = 0x803C2800
CHARACTER_MOTION_STATE_POINTERS = 0x803C12E0
FIGHTER_ACTION_COUNTS = 0x803C0FC8
COMMON_MOTION_STATE_COUNT = 0x155
MOTION_STATE_SIZE = 0x20
# FtMoveId_SpecialN through the final Kirby copied-neutral-special move ID.
SPECIAL_MOVE_IDS = frozenset(range(18, 48))


@dataclass(frozen=True, slots=True)
class FighterKindMetadata:
    """One internal fighter-kind row in the NTSC 1.02 executable tables."""

    code: str
    root_symbol: str
    action_count: int
    special_state_count: int


# Order is FighterKind, including bosses and wireframes omitted by Character.
FIGHTER_KINDS = (
    FighterKindMetadata("Mr", "ftDataMario", 303, 10),
    FighterKindMetadata("Fx", "ftDataFox", 327, 35),
    FighterKindMetadata("Ca", "ftDataCaptain", 318, 23),
    FighterKindMetadata("Dk", "ftDataDonkey", 337, 46),
    FighterKindMetadata("Kb", "ftDataKirby", 479, 203),
    FighterKindMetadata("Kp", "ftDataKoopa", 316, 23),
    FighterKindMetadata("Lk", "ftDataLink", 314, 21),
    FighterKindMetadata("Sk", "ftDataSeak", 317, 24),
    FighterKindMetadata("Ns", "ftDataNess", 326, 36),
    FighterKindMetadata("Pe", "ftDataPeach", 318, 30),
    FighterKindMetadata("Pp", "ftDataPopo", 321, 26),
    FighterKindMetadata("Nn", "ftDataNana", 321, 26),
    FighterKindMetadata("Pk", "ftDataPikachu", 320, 26),
    FighterKindMetadata("Ss", "ftDataSamus", 313, 18),
    FighterKindMetadata("Ys", "ftDataYoshi", 314, 28),
    FighterKindMetadata("Pr", "ftDataPurin", 327, 32),
    FighterKindMetadata("Mt", "ftDataMewtwo", 314, 20),
    FighterKindMetadata("Lg", "ftDataLuigi", 312, 18),
    FighterKindMetadata("Ms", "ftDataMars", 327, 32),
    FighterKindMetadata("Zd", "ftDataZelda", 311, 18),
    FighterKindMetadata("Cl", "ftDataClink", 314, 21),
    FighterKindMetadata("Dr", "ftDataDrmario", 303, 10),
    FighterKindMetadata("Fc", "ftDataFalco", 327, 35),
    FighterKindMetadata("Pc", "ftDataPichu", 320, 26),
    FighterKindMetadata("Gw", "ftDataGamewatch", 323, 40),
    FighterKindMetadata("Gn", "ftDataGanon", 318, 23),
    FighterKindMetadata("Fe", "ftDataEmblem", 327, 32),
    FighterKindMetadata("Mh", "ftDataMasterhand", 345, 50),
    FighterKindMetadata("Ch", "ftDataCrazyhand", 344, 49),
    FighterKindMetadata("Bo", "ftDataBoy", 295, 0),
    FighterKindMetadata("Gl", "ftDataGirl", 295, 0),
    FighterKindMetadata("Gk", "ftDataGkoopa", 316, 23),
    FighterKindMetadata("Sb", "ftDataSandbag", 296, 1),
)
FIGHTER_KINDS_BY_CODE = MappingProxyType({metadata.code: metadata for metadata in FIGHTER_KINDS})


__all__ = [
    "CHARACTER_MOTION_STATE_POINTERS",
    "COMMON_MOTION_STATE_COUNT",
    "COMMON_MOTION_STATE_TABLE",
    "DOLDECOMP_REVISION",
    "DOLDECOMP_SOURCE",
    "FIGHTER_ACTION_COUNTS",
    "FIGHTER_KINDS",
    "FIGHTER_KINDS_BY_CODE",
    "MOTION_STATE_SIZE",
    "SPECIAL_MOVE_IDS",
    "FighterKindMetadata",
]
