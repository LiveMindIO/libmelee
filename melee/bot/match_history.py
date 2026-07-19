"""Bot-facing match history dataclasses.

Pure data containers with no SQLite/FastAPI/Smithy dependencies. The runtime
constructs :class:`MatchHistory` instances from its persistence layer before
calling ``select_character`` on a bot.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from melee.enums import Character, Stage

MAX_PLAYERS = 4


class OtherPlayerRelation(StrEnum):
    """How another player in the match related to the viewing player."""

    TEAMMATE = "teammate"
    OPPONENT = "opponent"


class MatchRoundOutcome(StrEnum):
    COMPLETE = "complete"
    DNF = "dnf"


@dataclass(frozen=True)
class OtherPlayer:
    """Another player in the match from the viewing player's perspective."""

    relation: OtherPlayerRelation
    character: Character
    picked_stage: bool
    costume: int | None = None
    bot_name: str | None = None


@dataclass(frozen=True)
class PlayerMatchRecord:
    """One completed match from a single player's perspective."""

    player_selection: Character
    other_players: list[OtherPlayer]
    stage: Stage
    won: bool | None
    outcome: MatchRoundOutcome = MatchRoundOutcome.COMPLETE
    player_costume: int | None = None
    bot_name: str | None = None


@dataclass(frozen=True)
class MatchHistory:
    """Queryable match history indexed by controller port (1-4)."""

    _records_by_port: tuple[list[PlayerMatchRecord], ...]

    @classmethod
    def empty(cls) -> MatchHistory:
        return cls(_records_by_port=tuple([] for _ in range(MAX_PLAYERS)))

    @classmethod
    def from_port_lists(
        cls,
        records_by_port: list[list[PlayerMatchRecord]],
    ) -> MatchHistory:
        padded = [
            list(records_by_port[index]) if index < len(records_by_port) else []
            for index in range(MAX_PLAYERS)
        ]
        return cls(_records_by_port=tuple(padded))

    def records_for_port(self, port: int) -> list[PlayerMatchRecord]:
        return list(self._records_by_port[port - 1])

    def latest_for_port(self, port: int) -> PlayerMatchRecord | None:
        records = self.records_for_port(port)
        if not records:
            return None
        return records[-1]

    def records_for_bot(self, bot_name: str) -> list[PlayerMatchRecord]:
        return [
            record
            for port in self.all_ports()
            for record in self.records_for_port(port)
            if record.bot_name == bot_name
        ]

    def latest_for_bot(self, bot_name: str) -> PlayerMatchRecord | None:
        records = self.records_for_bot(bot_name)
        if not records:
            return None
        return records[-1]

    def all_ports(self) -> range:
        return range(1, MAX_PLAYERS + 1)
