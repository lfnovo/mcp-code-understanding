"""
Context generation and code analysis.
"""

from pathlib import Path
from typing import Dict, Any
import logging

from ..config import ContextConfig, load_config
from ..repository import Repository
from ..analysis.repo_map import RepoMapAnalyzer

logger = logging.getLogger(__name__)


class ContextGenerator:
    def __init__(self, config: ContextConfig):
        self.config = config
        self.repo_map_analyzer = RepoMapAnalyzer(config)

    async def generate_context(self, repo: Repository) -> str:
        """Generate structured context optimized for LLM consumption."""
        # Basic repo info in a format similar to Aider's
        repo_info = f"""Repository: {repo.id}
Type: {repo.repo_type}
Path: {repo.root_path}
Git: {'Yes' if repo.is_git else 'No'}
URL: {repo.url or 'N/A'}

Code Map:
"""
        # Get Aider's repo map
        repo_map = await self.repo_map_analyzer.analyze_repository(repo)

        # Combine and return
        return repo_info + repo_map
