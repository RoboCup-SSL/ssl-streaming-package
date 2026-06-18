from data_structures.domain import Team, MatchState
from data_structures.enums import Stage, Command


def test_matchstate_holds_teams_and_phase():
    state = MatchState(
        stage=Stage.NORMAL_FIRST_HALF,
        command=Command.NORMAL_START,
        blue=Team(name="ER-Force", score=1, yellow_cards=0),
        yellow=Team(name="TIGERs", score=2, yellow_cards=1),
    )
    assert state.blue.name == "ER-Force"
    assert state.yellow.score == 2
    assert state.stage is Stage.NORMAL_FIRST_HALF
    assert int(Command.GOAL_BLUE) == 15
