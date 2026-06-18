from data_structures.domain import MatchState
from data_structures.enums import Stage

_STAGE_LABELS = {
    Stage.NORMAL_FIRST_HALF_PRE: "Pre First Half",
    Stage.NORMAL_FIRST_HALF: "First Half",
    Stage.NORMAL_HALF_TIME: "Half Time",
    Stage.NORMAL_SECOND_HALF_PRE: "Pre Second Half",
    Stage.NORMAL_SECOND_HALF: "Second Half",
    Stage.EXTRA_TIME_BREAK: "Extra Time Break",
    Stage.EXTRA_FIRST_HALF_PRE: "Pre Extra First Half",
    Stage.EXTRA_FIRST_HALF: "Extra First Half",
    Stage.EXTRA_HALF_TIME: "Extra Half Time",
    Stage.EXTRA_SECOND_HALF_PRE: "Pre Extra Second Half",
    Stage.EXTRA_SECOND_HALF: "Extra Second Half",
    Stage.PENALTY_SHOOTOUT_BREAK: "Penalty Shootout Break",
    Stage.PENALTY_SHOOTOUT: "Penalty Shootout",
    Stage.POST_GAME: "Post Game",
}


def stage_label(stage: Stage) -> str:
    return _STAGE_LABELS[stage]


def format_updates(
    state: MatchState | None,
    schedule_view: dict | None,
    sources: dict[str, str],
) -> dict[str, str]:
    values: dict[str, str] = {}
    if state is not None:
        values["blue_name"] = state.blue.name
        values["blue_score"] = str(state.blue.score)
        values["yellow_name"] = state.yellow.name
        values["yellow_score"] = str(state.yellow.score)
        values["stage"] = stage_label(state.stage)
    if schedule_view is not None:
        nxt = schedule_view.get("next")
        if nxt is not None:
            values["next_match"] = nxt["matchup"]
        if schedule_view.get("countdown") is not None:
            values["countdown"] = schedule_view["countdown"]
    return {sources[key]: text for key, text in values.items() if key in sources}
