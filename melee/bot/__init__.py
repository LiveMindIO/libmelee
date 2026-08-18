"""Bot-facing Crowd Control API.

Bots import everything they need from :mod:`melee.bot` rather than the
``crowd_control`` runtime package. This keeps the bot author surface small and
self-contained: a bot file + libmelee is sufficient to develop and type-check
against.
"""

from melee.bot.character_state import (
    AttackType,
    CharacterState,
    CharacterStatus,
    attack_is_holdable,
    can_air_attack,
    can_attack,
    can_grab,
    can_jump,
    can_shield,
    can_taunt,
    can_z_air,
    get_state,
    in_hitstun,
    is_carrying_enemy,
    is_dodging,
    is_downed,
    is_getting_up,
    is_grabbed,
    is_grabbing,
    is_grabbing_ledge,
    is_shielding,
    is_shield_broken,
    is_taunting,
    neutral_b_is_chargeable,
    z_air_is_supported,
)
from melee.bot.input_montage import InputMontage, MontageState
from melee.bot.logger import BotLogger, BotLogEntry
from melee.bot.match_history import (
    MatchHistory,
    MatchRoundOutcome,
    OtherPlayer,
    OtherPlayerRelation,
    PlayerMatchRecord,
)
from melee.bot.protocol import CharacterSelection, CrowdControl
from melee.bot.simple_controls import (
    AttackFrameData,
    Hold,
    LedgeRecoveryOption,
    SimpleControls,
    StickReferenceAxis,
    stick_coordinates,
)
from melee.bot.techskill import (
    LedgedashMontage,
    MultishineMontage,
    PerfectPivotMontage,
    SDIMontage,
    WavedashDirection,
    WavedashMontage,
)

__all__ = [
    "AttackFrameData",
    "AttackType",
    "BotLogEntry",
    "BotLogger",
    "CharacterSelection",
    "CharacterState",
    "CharacterStatus",
    "CrowdControl",
    "Hold",
    "InputMontage",
    "LedgedashMontage",
    "LedgeRecoveryOption",
    "MatchHistory",
    "MatchRoundOutcome",
    "MontageState",
    "MultishineMontage",
    "OtherPlayer",
    "OtherPlayerRelation",
    "PerfectPivotMontage",
    "PlayerMatchRecord",
    "SDIMontage",
    "SimpleControls",
    "StickReferenceAxis",
    "WavedashDirection",
    "WavedashMontage",
    "attack_is_holdable",
    "can_air_attack",
    "can_attack",
    "can_grab",
    "can_jump",
    "can_shield",
    "can_taunt",
    "can_z_air",
    "get_state",
    "in_hitstun",
    "is_carrying_enemy",
    "is_dodging",
    "is_downed",
    "is_getting_up",
    "is_grabbed",
    "is_grabbing",
    "is_grabbing_ledge",
    "is_shielding",
    "is_shield_broken",
    "is_taunting",
    "neutral_b_is_chargeable",
    "stick_coordinates",
    "z_air_is_supported",
]
