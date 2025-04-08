"""
Clone repository MCP tool implementation.
"""

from typing import Dict, Any, Optional
from fastmcp import BaseTool

from ..repository.manager import RepositoryManager


class CloneRepoTool(BaseTool):
    """Tool for cloning Git repositories."""

    def __init__(self, repo_manager: RepositoryManager):
        self.repo_manager = repo_manager

    async def __call__(self, url: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """Clone a Git repository.

        Args:
            url: Repository URL to clone
            branch: Optional branch to clone (defaults to default branch)

        Returns:
            Dict containing status and repository information
        """
        return await self.repo_manager.clone_repository(url, branch)
