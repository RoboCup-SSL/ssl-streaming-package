from dataclasses import dataclass, field


@dataclass(frozen=True)
class GameControllerConfig:
    address: str
    port: int


@dataclass(frozen=True)
class ObsConfig:
    url: str
    password: str
    sources: dict[str, str] = field(default_factory=dict)
    images: dict[str, str] = field(default_factory=dict)
    logos_dir: str = "logos"
    stage_dir: str = ""
    text_field: str = "text"
