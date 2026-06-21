from dataclasses import dataclass


@dataclass(frozen=True)
class GameControllerConfig:
    address: str
    port: int


@dataclass(frozen=True)
class ObsConfig:
    url: str
    password: str
    logos_dir: str = ""
    stage_dir: str = ""
    text_field: str = "text"
