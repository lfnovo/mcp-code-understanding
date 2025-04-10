"""
Context generation and code analysis.
"""

from pathlib import Path
from typing import Dict, Any, List
import asyncio
import logging

from ..config import ContextConfig, load_config
from ..repository import Repository
from ..parsers.base import BaseParser
from ..parsers import create_parsers  # Import the factory function

logger = logging.getLogger(__name__)


class ContextGenerator:
    def __init__(self, config: ContextConfig):
        # Get complete config to pass to create_parsers
        try:
            full_config = load_config()

            # Use the factory to create parsers
            self.parsers_list = create_parsers(full_config)
            logger.info(f"Initialized {len(self.parsers_list)} parsers")
        except Exception as e:
            logger.error(f"Error initializing parsers: {e}")
            self.parsers_list = []

        self.config = config

    async def generate_context(self, repo: Repository) -> Dict[str, Any]:
        """Generate structured context for a repository."""
        context = {
            "repository": {
                "id": repo.id,
                "type": repo.repo_type,
                "path": str(repo.root_path),
                "is_git": repo.is_git,
                "url": repo.url,
            },
            "structure": await self._analyze_structure(repo),
            "summary": await self._generate_summary(repo),
        }

        return context

    async def _analyze_structure(self, repo: Repository) -> Dict[str, Any]:
        """Analyze the repository structure."""
        structure = {"files": [], "directories": []}

        root = repo.root_path
        for path in root.rglob("*"):
            rel_path = path.relative_to(root)

            # Skip common directories to ignore and gitignored files
            if any(p.startswith(".") for p in path.parts) or repo.is_ignored(rel_path):
                continue

            if path.is_file():
                structure["files"].append(str(rel_path))
            else:
                structure["directories"].append(str(rel_path))

        return structure

    async def _generate_summary(self, repo: Repository) -> Dict[str, Any]:
        """Generate a high-level summary of the repository."""
        summary = {
            "file_stats": {
                "total_files": 0,
                "total_directories": 0,
                "by_extension": {},
            },
            "parsed_files": [],
        }

        # Gather basic stats
        for path in repo.root_path.rglob("*"):
            # Skip common directories to ignore and gitignored files
            if any(p.startswith(".") for p in path.parts) or repo.is_ignored(path):
                continue

            if path.is_file():
                summary["file_stats"]["total_files"] += 1
                ext = path.suffix.lower()
                summary["file_stats"]["by_extension"][ext] = (
                    summary["file_stats"]["by_extension"].get(ext, 0) + 1
                )
            else:
                summary["file_stats"]["total_directories"] += 1

        # Parse files using Tree-sitter
        parsed_count = 0
        for path in repo.root_path.rglob("*"):
            if not path.is_file():
                continue

            # Skip common directories to ignore and gitignored files
            if any(p.startswith(".") for p in path.parts) or repo.is_ignored(path):
                continue

            # Find parser that can handle this file
            parser = next(
                (p for p in self.parsers_list if p.can_parse(str(path))), None
            )

            if parser and parsed_count < self.config.max_files_per_context:
                try:
                    content = path.read_text(errors="replace")
                    parsed = await parser.parse_file(content, str(path))
                    summary["parsed_files"].append(parsed)
                    parsed_count += 1
                    logger.debug(f"Successfully parsed {path}")
                except Exception as e:
                    logger.error(f"Error parsing {path}: {e}")

        return summary
