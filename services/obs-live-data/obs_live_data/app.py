from data_processing.format import format_updates


async def run_referee(source, obs, sources: dict[str, str]) -> None:
    """Push live referee-derived text to OBS, sending only fields whose value
    changed since the last push (last-write-wins)."""
    last: dict[str, str] = {}
    async for state in source:
        updates = format_updates(state, None, sources)
        for name, value in updates.items():
            if last.get(name) != value:
                await obs.set_text(name, value)
                last[name] = value
