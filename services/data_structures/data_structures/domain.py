from dataclasses import dataclass

from data_structures.enums import Command, Stage


@dataclass(frozen=True)
class Team:
    name: str
    score: int
    yellow_cards: int
    red_cards: int = 0
    yellow_card_times: tuple[int, ...] = ()
    timeout_time: int = 0
    substitution_allowed: bool = False
    substitution_intent: bool = False
    substitution_time_left: int = 0


@dataclass(frozen=True)
class MatchState:
    stage: Stage
    command: Command
    blue: Team
    yellow: Team
    stage_time_left: int = 0
    next_command: Command | None = None
    action_time_remaining: int = 0
