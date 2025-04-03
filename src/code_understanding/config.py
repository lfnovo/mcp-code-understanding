"""
Configuration management for the Code Understanding server.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml

@dataclass
class ServerConfig:
    name: str
    log_level: str
    host: str
    port: int

@dataclass
class GitHubConfig:
    api_token: str

@dataclass
class RepositoryConfig:
    cache_dir: Path
    refresh_interval: int
    github: GitHubConfig

@dataclass
class ContextConfig:
    summary_depth: str
    include_dependencies: bool
    max_files_per_context: int

@dataclass
class ParserConfig:
    enabled: List[str]

@dataclass
class Config:
    server: ServerConfig
    repositories: RepositoryConfig
    context: ContextConfig
    parsers: ParserConfig

def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = Path("config.yaml")
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    return Config(
        server=ServerConfig(
            name=data["server"]["name"],
            log_level=data["server"]["log_level"],
            host=data["server"]["host"],
            port=data["server"]["port"]
        ),
        repositories=RepositoryConfig(
            cache_dir=Path(data["repositories"]["cache_dir"]),
            refresh_interval=data["repositories"]["refresh_interval"],
            github=GitHubConfig(
                api_token=data["repositories"]["github"]["api_token"]
            )
        ),
        context=ContextConfig(
            summary_depth=data["context"]["summary_depth"],
            include_dependencies=data["context"]["include_dependencies"],
            max_files_per_context=data["context"]["max_files_per_context"]
        ),
        parsers=ParserConfig(
            enabled=data["parsers"]["enabled"]
        )
    )
