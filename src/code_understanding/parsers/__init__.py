"""Parser factory."""

from typing import List, Dict
from pathlib import Path

from .base import BaseParser
from .treesitter_adapter import TreeSitterParser


def create_parsers(config: Dict) -> List[BaseParser]:
    """Create parser instances based on configuration.

    Args:
        config: Application configuration

    Returns:
        List of parser instances
    """
    parsers = []

    # Add TreeSitter parser
    queries_path = Path(config["treesitter"]["queries_path"])
    treesitter_parser = TreeSitterParser(queries_path)
    parsers.append(treesitter_parser)

    return parsers
