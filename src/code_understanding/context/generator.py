"""
Context generation and code analysis.
"""

from pathlib import Path
from typing import Dict, Any, List
import asyncio

from tree_sitter import Language, Parser

from ..config import ContextConfig
from ..repository import Repository
from ..parsers.base import BaseParser
from ..parsers.python import PythonParser


class ContextGenerator:
    def __init__(self, config: ContextConfig):
        self.config = config
        self.parsers: Dict[str, BaseParser] = {".py": PythonParser()}

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

        if self.config.include_dependencies:
            context["dependencies"] = await self._analyze_dependencies(repo)

        return context

    async def _analyze_structure(self, repo: Repository) -> Dict[str, Any]:
        """Analyze the repository structure."""
        structure = {"files": [], "directories": [], "entry_points": [], "packages": []}

        root = repo.root_path
        for path in root.rglob("*"):
            rel_path = path.relative_to(root)

            # Skip common directories to ignore
            if any(p.startswith(".") for p in path.parts):
                continue

            if path.is_file():
                structure["files"].append(str(rel_path))

                # Identify potential entry points
                if path.name in ["main.py", "app.py", "server.py"]:
                    structure["entry_points"].append(str(rel_path))
            else:
                if path.is_dir() and (path / "__init__.py").exists():
                    structure["packages"].append(str(rel_path))
                else:
                    structure["directories"].append(str(rel_path))

        return structure

    async def _analyze_dependencies(self, repo: Repository) -> Dict[str, Any]:
        """Analyze project dependencies."""
        deps = {"python": {"requirements": [], "poetry": None, "pipfile": None}}

        # Check requirements.txt
        req_file = repo.root_path / "requirements.txt"
        if req_file.exists():
            deps["python"]["requirements"] = req_file.read_text().splitlines()

        # Check pyproject.toml
        pyproject = repo.root_path / "pyproject.toml"
        if pyproject.exists():
            deps["python"]["poetry"] = pyproject.read_text()

        # Check Pipfile
        pipfile = repo.root_path / "Pipfile"
        if pipfile.exists():
            deps["python"]["pipfile"] = pipfile.read_text()

        return deps

    async def _generate_summary(self, repo: Repository) -> Dict[str, Any]:
        """Generate a high-level summary of the repository."""
        summary = {
            "file_count": 0,
            "directory_count": 0,
            "language_stats": {},
            "parsed_files": [],
        }

        # Gather basic stats
        for path in repo.root_path.rglob("*"):
            if path.is_file():
                summary["file_count"] += 1
                ext = path.suffix
                summary["language_stats"][ext] = (
                    summary["language_stats"].get(ext, 0) + 1
                )
            else:
                summary["directory_count"] += 1

        # Parse files up to the configured limit
        parsed_count = 0
        for path in repo.root_path.rglob("*"):
            if not path.is_file():
                continue

            parser = self.parsers.get(path.suffix)
            if parser and parsed_count < self.config.max_files_per_context:
                try:
                    content = path.read_text()
                    parsed = await parser.parse_file(content, str(path))
                    summary["parsed_files"].append(parsed)
                    parsed_count += 1
                except Exception as e:
                    print(f"Error parsing {path}: {e}")

        return summary
