"""
Configuration management for the Code Understanding server.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict
import yaml
import os
import logging
import platform
import shutil
import importlib.resources
from platformdirs import user_config_dir


@dataclass
class IndexerConfig:
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embeddings_model: str = "all-MiniLM-L6-v2"
    vector_db_path: str = "./vector_db"

    def __post_init__(self):
        # Expand ~ to home directory in vector_db_path
        self.vector_db_path = os.path.expanduser(self.vector_db_path)


@dataclass
class DocumentationConfig:
    include_tags: List[str] = None
    include_extensions: List[str] = None
    format_mapping: Dict[str, str] = None
    category_patterns: Dict[str, List[str]] = None

    def __post_init__(self):
        # Set default values if not provided
        if self.include_tags is None:
            self.include_tags = ["markdown", "rst", "adoc"]
        if self.include_extensions is None:
            self.include_extensions = [".md", ".markdown", ".rst", ".txt", ".adoc", ".ipynb"]
        if self.format_mapping is None:
            self.format_mapping = {
                # Tag-based format mapping
                "tag:markdown": "markdown",
                "tag:rst": "restructuredtext",
                "tag:adoc": "asciidoc",
                # Extension-based format mapping
                "ext:.md": "markdown",
                "ext:.markdown": "markdown",
                "ext:.rst": "restructuredtext",
                "ext:.txt": "plaintext",
                "ext:.adoc": "asciidoc",
                "ext:.ipynb": "jupyter"
            }
        if self.category_patterns is None:
            self.category_patterns = {
                "readme": ["readme"],
                "api": ["api"],
                "documentation": ["docs", "documentation"],
                "examples": ["examples", "sample"]
            }


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
        # Expand ~ to home directory in cache_dir
        self.cache_dir = os.path.expanduser(self.cache_dir)


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
    documentation: DocumentationConfig = None

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
        if self.documentation is None:
            self.documentation = DocumentationConfig()


def ensure_default_config() -> None:
    """Ensure default config exists in the standard .config directory."""
    logger = logging.getLogger(__name__)
    
    # Use ~/.config/mcp-code-understanding for both Linux and macOS
    config_dir = Path.home() / ".config" / "mcp-code-understanding"
    config_path = config_dir / "config.yaml"
    
    if not config_path.exists():
        # Create parent directories if they don't exist
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy default config from package
        try:
            # Try to find the config file relative to this file
            current_dir = Path(__file__).resolve().parent
            default_config_path = current_dir / "config" / "config.yaml"
            
            if default_config_path.exists():
                with open(default_config_path, 'r') as src:
                    default_config = src.read()
                    with open(config_path, 'w') as dst:
                        dst.write(default_config)
                logger.info(f"Created default configuration at {config_path}")
            else:
                logger.error(f"Could not find default config at {default_config_path}")
                raise FileNotFoundError(f"Default config not found at {default_config_path}")
        except Exception as e:
            logger.error(f"Failed to create default config: {e}")
            raise


def get_config_search_paths() -> List[str]:
    """Get list of paths to search for config file."""
    paths = []
    
    # Check if we're running from an installed package or in development mode
    # If __file__ is in a site-packages directory, we're running from an installed package
    if "site-packages" in __file__:
        # Installed mode - check standard location first
        config_dir = Path.home() / ".config" / "mcp-code-understanding"
        paths.append(str(config_dir / "config.yaml"))
        
        # Fallback to current directory only for backward compatibility
        paths.append("./config.yaml")
    else:
        # Development mode - check current directory first
        paths.append("./config.yaml")
        
        # Then check standard location
        config_dir = Path.home() / ".config" / "mcp-code-understanding"
        paths.append(str(config_dir / "config.yaml"))
    
    return paths


def load_config(config_path: str = None) -> ServerConfig:
    """Load configuration from YAML file."""
    logger = logging.getLogger(__name__)

    # Always ensure default config exists first
    ensure_default_config()

    # If config_path is explicitly provided, only try that one
    if config_path:
        search_paths = [config_path]
    else:
        search_paths = get_config_search_paths()

    # Try each path in order
    for path in search_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            logger.info(f"Loading configuration from {abs_path}")
            with open(abs_path, "r") as f:
                config_data = yaml.safe_load(f)

            if not config_data:
                logger.warning(f"Config file {abs_path} is empty, trying next location")
                continue

            logger.debug(f"Loaded configuration data: {config_data}")

            # Convert nested dictionaries to appropriate config objects
            if "repository" in config_data and isinstance(config_data["repository"], dict):
                github_config = None
                if "github" in config_data["repository"]:
                    github_config = GitHubConfig(**config_data["repository"].pop("github"))
                config_data["repository"] = RepositoryConfig(**config_data["repository"], github=github_config)

            if "context" in config_data and isinstance(config_data["context"], dict):
                config_data["context"] = ContextConfig(**config_data["context"])

            if "parser" in config_data and isinstance(config_data["parser"], dict):
                config_data["parser"] = ParserConfig(**config_data["parser"])

            if "indexer" in config_data and isinstance(config_data["indexer"], dict):
                config_data["indexer"] = IndexerConfig(**config_data["indexer"])

            if "treesitter" in config_data and isinstance(config_data["treesitter"], dict):
                config_data["treesitter"] = TreeSitterConfig(**config_data["treesitter"])

            if "documentation" in config_data and isinstance(config_data["documentation"], dict):
                config_data["documentation"] = DocumentationConfig(**config_data["documentation"])

            return ServerConfig(**config_data)

    # If we get here, something went wrong with creating/reading the config
    logger.error(f"Failed to load or create config in: {', '.join(search_paths)}")
    return ServerConfig()
