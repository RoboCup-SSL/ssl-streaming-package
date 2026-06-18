from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage
from data_structures.proto import ssl_gc_referee_pb2 as pb


def _team(info: pb.Referee.TeamInfo) -> Team:
    return Team(name=info.name, score=info.score, yellow_cards=info.yellow_cards)


def decode_referee(payload: bytes) -> MatchState:
    ref = pb.Referee()
    ref.ParseFromString(payload)
    return MatchState(
        stage=Stage(ref.stage),
        command=Command(ref.command),
        blue=_team(ref.blue),
        yellow=_team(ref.yellow),
    )
