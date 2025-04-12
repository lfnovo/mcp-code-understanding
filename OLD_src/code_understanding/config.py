"""
Configuration management for the Code Understanding server.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import yaml
import os


@dataclass
class IndexerConfig:
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embeddings_model: str = "all-MiniLM-L6-v2"
    vector_db_path: str = "./vector_db"


@dataclass
class TreeSitterConfig:
    queries_path: str = "./src/code_understanding/treesitter/queries"
    enabled_languages: List[str] = None

    def __post_init__(self):
        if self.enabled_languages is None:
            self.enabled_languages = [
                "python",
                "javascript",
                "typescript",
                "java",
                "go",
            ]


@dataclass
class GitHubConfig:
    api_token: Optional[str] = None


@dataclass
class RepositoryConfig:
    cache_dir: str = "./repo_cache"
    refresh_interval: int = 3600  # seconds
    max_cached_repos: int = 50
    github: Optional[GitHubConfig] = None

    def __post_init__(self):
        if self.github is None:
            self.github = GitHubConfig()


@dataclass
class ContextConfig:
    summary_depth: int = 2
    include_dependencies: bool = True
    max_files_per_context: int = 10


@dataclass
class ParserConfig:
    enabled_languages: List[str] = None

    def __post_init__(self):
        if self.enabled_languages is None:
            self.enabled_languages = [
                "python",
                "javascript",
                "typescript",
                "java",
                "go",
            ]


@dataclass
class ServerConfig:
    name: str = "Code Understanding Server"
    log_level: str = "info"
    host: str = "localhost"
    port: int = 8080
    repository: RepositoryConfig = None
    context: ContextConfig = None
    parser: ParserConfig = None
    indexer: IndexerConfig = None
    treesitter: TreeSitterConfig = None

    def __post_init__(self):
        if self.repository is None:
            self.repository = RepositoryConfig()
        if self.context is None:
            self.context = ContextConfig()
        if self.parser is None:
            self.parser = ParserConfig()
        if self.indexer is None:
            self.indexer = IndexerConfig()
        if self.treesitter is None:
            self.treesitter = TreeSitterConfig()


def load_config(config_path: str = "config.yaml") -> ServerConfig:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        return ServerConfig()

    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    if not config_data:
        return ServerConfig()

    # Convert nested dictionaries to appropriate config objects
    if "repository" in config_data and isinstance(config_data["repository"], dict):
        github_config = None
        if "github" in config_data["repository"]:
            github_config = GitHubConfig(**config_data["repository"].pop("github"))
        config_data["repository"] = RepositoryConfig(
            **config_data["repository"], github=github_config
        )

    if "context" in config_data and isinstance(config_data["context"], dict):
        config_data["context"] = ContextConfig(**config_data["context"])

    if "parser" in config_data and isinstance(config_data["parser"], dict):
        config_data["parser"] = ParserConfig(**config_data["parser"])

    if "indexer" in config_data and isinstance(config_data["indexer"], dict):
        config_data["indexer"] = IndexerConfig(**config_data["indexer"])

    if "treesitter" in config_data and isinstance(config_data["treesitter"], dict):
        config_data["treesitter"] = TreeSitterConfig(**config_data["treesitter"])

    return ServerConfig(**config_data)
