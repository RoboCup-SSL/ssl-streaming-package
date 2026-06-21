from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage
from data_structures.proto import ssl_gc_referee_pb2 as pb


def _team(info: pb.Referee.TeamInfo) -> Team:
    return Team(
        name=info.name,
        score=info.score,
        yellow_cards=info.yellow_cards,
        red_cards=info.red_cards,
        yellow_card_times=tuple(info.yellow_card_times),
        timeout_time=info.timeout_time,
        substitution_allowed=info.bot_substitution_allowed,
        substitution_intent=info.bot_substitution_intent,
        substitution_time_left=info.bot_substitution_time_left,
    )


def decode_referee(payload: bytes) -> MatchState:
    ref = pb.Referee()
    ref.ParseFromString(payload)
    return MatchState(
        stage=Stage(ref.stage),
        command=Command(ref.command),
        blue=_team(ref.blue),
        yellow=_team(ref.yellow),
        stage_time_left=ref.stage_time_left,
        next_command=Command(ref.next_command) if ref.HasField("next_command") else None,
        action_time_remaining=ref.current_action_time_remaining,
    )
