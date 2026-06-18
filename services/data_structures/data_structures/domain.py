from dataclasses import dataclass

from data_structures.enums import Command, Stage


@dataclass(frozen=True)
class Team:
    name: str
    score: int
    yellow_cards: int


@dataclass(frozen=True)
class MatchState:
    stage: Stage
    command: Command
    blue: Team
    yellow: Team
