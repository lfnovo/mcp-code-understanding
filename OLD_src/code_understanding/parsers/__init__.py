"""Parser factory and utilities."""

from pathlib import Path
from typing import Dict, List

from ..config import ServerConfig
from .base import BaseParser
from .treesitter_adapter import TreeSitterParser


def create_parsers(config: ServerConfig) -> List[BaseParser]:
    """Create parser instances based on config.

    Args:
        config: Server configuration

    Returns:
        List of parser instances
    """
    parsers = []

    # Add TreeSitter parser
    queries_path = Path(config.treesitter.queries_path)
    treesitter_parser = TreeSitterParser(queries_path)
    parsers.append(treesitter_parser)

    return parsers
