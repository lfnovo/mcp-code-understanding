"""
Refresh repository MCP tool implementation.
"""

from typing import Dict, Any, Optional
from fastmcp import BaseTool

from ..repository.manager import RepositoryManager


class RefreshRepoTool(BaseTool):
    """Tool for refreshing Git repositories."""

    def __init__(self, repo_manager: RepositoryManager):
        self.repo_manager = repo_manager

    async def __call__(self, repo_path: str) -> Dict[str, Any]:
        """Refresh a Git repository with latest changes.

        Args:
            repo_path: Path to the repository to refresh

        Returns:
            Dict containing status and repository information
        """
        return await self.repo_manager.refresh_repository(repo_path)
