import tomllib
from dataclasses import dataclass

from data_access.config import GameControllerConfig, ObsConfig
from data_processing.schedule import ScheduleConfig


@dataclass(frozen=True)
class FieldConfig:
    name: str
    game_controller: GameControllerConfig
    obs: ObsConfig
    schedule: ScheduleConfig

    @classmethod
    def load_from_file(cls, path: str) -> "FieldConfig":
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        obs = data["obs"]
        return cls(
            name=data["field"]["name"],
            game_controller=GameControllerConfig(**data["game_controller"]),
            obs=ObsConfig(
                url=obs["url"],
                password=obs["password"],
                sources=dict(obs.get("sources", {})),
                images=dict(obs.get("images", {})),
                logos_dir=obs.get("logos_dir", ""),
                stage_dir=obs.get("stage_dir", ""),
                text_field=obs.get("text_field", "text"),
            ),
            schedule=ScheduleConfig(path=data["schedule"]["path"]),
        )
