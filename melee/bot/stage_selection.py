"""Immutable opponent evidence supplied by an embedding runtime before stage select."""

from __future__ import annotations

from dataclasses import dataclass

from melee.enums import Character, Stage


@dataclass(frozen=True)
class StageBan:
    stage: Stage
    bot_id: str | None
    bot_name: str | None
    port: int
    fallback: bool = False


@dataclass(frozen=True)
class StageMatchup:
    round_id: str
    character: Character
    opponents: tuple[Character, ...]
    stage: Stage
    won: bool | None
    dnf: bool
    bans: tuple[StageBan, ...] = ()
    chooser_bot_id: str | None = None
    selected_stage: Stage | None = None


@dataclass(frozen=True)
class CharacterStageWinRate:
    character: Character
    stage: Stage
    wins: int
    losses: int
    dnfs: int

    @property
    def win_rate(self) -> float | None:
        decisive = self.wins + self.losses
        return self.wins / decisive if decisive else None


@dataclass(frozen=True)
class StageSelectionHistory:
    """Opponent's full durable history, plus current character picks and strikes.

    Rates include all opponents and revisions. DNF is never a loss. Historical
    bans are unavailable for rounds recorded before stage-striking support.
    """

    opponent_bot_id: str
    opponent_bot_name: str
    player_character: Character
    opponent_character: Character
    matchups: tuple[StageMatchup, ...]
    win_rates: tuple[CharacterStageWinRate, ...]
    current_bans: tuple[StageBan, ...] = ()
