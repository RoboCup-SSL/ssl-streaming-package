import math

from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage

_STAGE_LABELS = {
    Stage.NORMAL_FIRST_HALF_PRE: "Match to be started",
    Stage.NORMAL_FIRST_HALF: "1st Half",
    Stage.NORMAL_HALF_TIME: "Half Time",
    Stage.NORMAL_SECOND_HALF_PRE: "2nd Half",
    Stage.NORMAL_SECOND_HALF: "2nd Half",
    Stage.EXTRA_TIME_BREAK: "Game goes into Overtime",
    Stage.EXTRA_FIRST_HALF_PRE: "1st Half (Overtime)",
    Stage.EXTRA_FIRST_HALF: "1st Half (Overtime)",
    Stage.EXTRA_HALF_TIME: "Half Time (Overtime)",
    Stage.EXTRA_SECOND_HALF_PRE: "2nd Half (Overtime)",
    Stage.EXTRA_SECOND_HALF: "2nd Half (Overtime)",
    Stage.PENALTY_SHOOTOUT_BREAK: "Prepare for Penalty Shootout",
    Stage.PENALTY_SHOOTOUT: "Penalty Shootout",
    Stage.POST_GAME: "Match finished",
}

# Command -> human text with the team embedded (the status board conveys the team via
# colour; a plain OBS text source carries it in words instead).
_COMMAND_TEXT = {
    Command.HALT: "Halt",
    Command.STOP: "Stop",
    Command.NORMAL_START: "Normal Start",
    Command.FORCE_START: "Force Start",
    Command.PREPARE_KICKOFF_YELLOW: "Kickoff for Yellow",
    Command.PREPARE_KICKOFF_BLUE: "Kickoff for Blue",
    Command.PREPARE_PENALTY_YELLOW: "Penalty Kick for Yellow",
    Command.PREPARE_PENALTY_BLUE: "Penalty Kick for Blue",
    Command.DIRECT_FREE_YELLOW: "Free Kick for Yellow",
    Command.DIRECT_FREE_BLUE: "Free Kick for Blue",
    Command.INDIRECT_FREE_YELLOW: "Free Kick for Yellow",
    Command.INDIRECT_FREE_BLUE: "Free Kick for Blue",
    Command.TIMEOUT_YELLOW: "Timeout for Yellow",
    Command.TIMEOUT_BLUE: "Timeout for Blue",
    Command.GOAL_YELLOW: "Goal for Yellow",
    Command.GOAL_BLUE: "Goal for Blue",
    Command.BALL_PLACEMENT_YELLOW: "Ball Placement for Yellow",
    Command.BALL_PLACEMENT_BLUE: "Ball Placement for Blue",
}


def stage_label(stage: Stage) -> str:
    return _STAGE_LABELS[stage]


def format_clock(microseconds: int) -> str:
    """Match the status board's formatDuration: 0 -> '0:00', else 'MM:SS' (both padded),
    ceiling of seconds, '-' prefix when negative (overtime)."""
    if microseconds == 0:
        return "0:00"
    sign = "-" if microseconds < 0 else ""
    total = math.ceil(abs(microseconds) / 1_000_000)
    minutes, seconds = divmod(total, 60)
    return f"{sign}{minutes:02d}:{seconds:02d}"


def command_text(state: MatchState) -> str:
    text = _COMMAND_TEXT[state.command]
    if state.command in (Command.BALL_PLACEMENT_BLUE, Command.BALL_PLACEMENT_YELLOW):
        if state.action_time_remaining >= 0:
            text += f" ({format_clock(state.action_time_remaining)})"
    elif state.command is Command.TIMEOUT_BLUE:
        text += f" ({format_clock(state.blue.timeout_time)})"
    elif state.command is Command.TIMEOUT_YELLOW:
        text += f" ({format_clock(state.yellow.timeout_time)})"
    return text


def next_command_text(command: Command | None) -> str:
    if command is None:
        return ""
    return f"Next: {_COMMAND_TEXT[command]}"


def substitution_text(team: Team) -> str:
    if team.substitution_allowed:
        text = "Substitution Active"
    elif team.substitution_intent:
        text = "Substitution Requested"
    else:
        return ""
    if team.substitution_time_left > 0:
        text += f" ({format_clock(team.substitution_time_left)})"
    return text


def card_time_texts(team: Team) -> list[str]:
    return [format_clock(t) for t in team.yellow_card_times[:2]]


def format_updates(state: MatchState) -> dict[str, str]:
    """Canonical source name -> display string for every scoreboard field. Pushed
    deduped; the key is the OBS source name."""
    updates = {
        "blue_name": state.blue.name,
        "yellow_name": state.yellow.name,
        "blue_score": str(state.blue.score),
        "yellow_score": str(state.yellow.score),
        "stage": stage_label(state.stage),
        "stage_time": format_clock(state.stage_time_left),
        "command": command_text(state),
        "next_command": next_command_text(state.next_command),
        "blue_yellow_cards": str(state.blue.yellow_cards),
        "yellow_yellow_cards": str(state.yellow.yellow_cards),
        "blue_red_cards": str(state.blue.red_cards),
        "yellow_red_cards": str(state.yellow.red_cards),
        "blue_substitution": substitution_text(state.blue),
        "yellow_substitution": substitution_text(state.yellow),
    }
    for side, team in (("blue", state.blue), ("yellow", state.yellow)):
        times = card_time_texts(team)
        for i in range(2):
            updates[f"{side}_card_time_{i + 1}"] = times[i] if i < len(times) else ""
    return updates
