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


# Command -> coarse play state (no team), the status board's center line. The team is
# carried separately by command_text(); this is the "Game is Running / Halted" summary.
_GAME_STATE_TEXT = {
    Command.HALT: "Game is Halted",
    Command.STOP: "Game is Stopped",
    Command.NORMAL_START: "Game is Running",
    Command.FORCE_START: "Game is Running",
    Command.PREPARE_KICKOFF_YELLOW: "Kickoff",
    Command.PREPARE_KICKOFF_BLUE: "Kickoff",
    Command.PREPARE_PENALTY_YELLOW: "Penalty Kick",
    Command.PREPARE_PENALTY_BLUE: "Penalty Kick",
    Command.DIRECT_FREE_YELLOW: "Game is Running",
    Command.DIRECT_FREE_BLUE: "Game is Running",
    Command.INDIRECT_FREE_YELLOW: "Game is Running",
    Command.INDIRECT_FREE_BLUE: "Game is Running",
    Command.TIMEOUT_YELLOW: "Timeout",
    Command.TIMEOUT_BLUE: "Timeout",
    Command.GOAL_YELLOW: "Goal",
    Command.GOAL_BLUE: "Goal",
    Command.BALL_PLACEMENT_YELLOW: "Ball Placement",
    Command.BALL_PLACEMENT_BLUE: "Ball Placement",
}


def stage_label(stage: Stage) -> str:
    return _STAGE_LABELS[stage]


def game_state_text(command: Command) -> str:
    return _GAME_STATE_TEXT[command]


def _abgr(r: int, g: int, b: int, a: int = 0xFF) -> int:
    """OBS color sources store colour as a single 0xAABBGGRR integer."""
    return (a << 24) | (b << 16) | (g << 8) | r


# Match the status board's team colours (assets/global.css): blue #779fff, yellow #fff145.
_TEAM_BLUE = _abgr(0x77, 0x9F, 0xFF)
_TEAM_YELLOW = _abgr(0xFF, 0xF1, 0x45)
_TRANSPARENT = 0

_BLUE_COMMANDS = {
    Command.PREPARE_KICKOFF_BLUE, Command.PREPARE_PENALTY_BLUE,
    Command.DIRECT_FREE_BLUE, Command.INDIRECT_FREE_BLUE,
    Command.TIMEOUT_BLUE, Command.GOAL_BLUE, Command.BALL_PLACEMENT_BLUE,
}
_YELLOW_COMMANDS = {
    Command.PREPARE_KICKOFF_YELLOW, Command.PREPARE_PENALTY_YELLOW,
    Command.DIRECT_FREE_YELLOW, Command.INDIRECT_FREE_YELLOW,
    Command.TIMEOUT_YELLOW, Command.GOAL_YELLOW, Command.BALL_PLACEMENT_YELLOW,
}


def command_color(command: Command) -> int:
    """OBS colour for the team the current command applies to; transparent when the
    command has no team (Halt/Stop/Normal Start), so a backing Color source hides itself."""
    if command in _BLUE_COMMANDS:
        return _TEAM_BLUE
    if command in _YELLOW_COMMANDS:
        return _TEAM_YELLOW
    return _TRANSPARENT


def format_colors(state: MatchState) -> dict[str, int]:
    """Canonical Color-source name -> OBS colour int."""
    return {"command_color": command_color(state.command)}


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
        "game_state": game_state_text(state.command),
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
