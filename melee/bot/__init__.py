"""Bot-facing Crowd Control API.

Bots import everything they need from :mod:`melee.bot` rather than the
``crowd_control`` runtime package. This keeps the bot author surface small and
self-contained: a bot file + libmelee is sufficient to develop and type-check
against.
"""

from melee.bot.character_specific_controls import (
    NO_OVERRIDE,
    CharacterSpecificControls,
    CharacterSpecificControlsFactory,
    NoOverride,
)
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
    AttackType,
    CharacterStatus,
    Hold,
    LedgeRecoveryOption,
    SimpleControls,
    attack_is_holdable,
    can_air_attack,
    can_attack,
    can_grab,
    can_shield,
    can_taunt,
    can_z_air,
    get_state,
    in_hitstun,
    is_carrying_enemy,
    is_dodging,
    is_grabbed,
    is_grabbing,
    is_grabbing_ledge,
    is_shielding,
    is_shield_broken,
    is_taunting,
    neutral_b_is_chargeable,
    z_air_is_supported,
)

__all__ = [
    "AttackFrameData",
    "AttackType",
    "BotLogEntry",
    "BotLogger",
    "CharacterSelection",
    "CharacterSpecificControls",
    "CharacterSpecificControlsFactory",
    "CharacterStatus",
    "CrowdControl",
    "Hold",
    "LedgeRecoveryOption",
    "MatchHistory",
    "MatchRoundOutcome",
    "NO_OVERRIDE",
    "NoOverride",
    "OtherPlayer",
    "OtherPlayerRelation",
    "PlayerMatchRecord",
    "SimpleControls",
    "attack_is_holdable",
    "can_air_attack",
    "can_attack",
    "can_grab",
    "can_shield",
    "can_taunt",
    "can_z_air",
    "get_state",
    "in_hitstun",
    "is_carrying_enemy",
    "is_dodging",
    "is_grabbed",
    "is_grabbing",
    "is_grabbing_ledge",
    "is_shielding",
    "is_shield_broken",
    "is_taunting",
    "neutral_b_is_chargeable",
    "z_air_is_supported",
]
