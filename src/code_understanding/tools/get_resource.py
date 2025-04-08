"""
Get resource MCP tool implementation.
"""

from typing import Dict, Any
from fastmcp import BaseTool

from ..repository.manager import RepositoryManager


class GetResourceTool(BaseTool):
    """Tool for retrieving repository resources."""

    def __init__(self, repo_manager: RepositoryManager):
        self.repo_manager = repo_manager

    async def __call__(self, repo_path: str, resource_path: str) -> Dict[str, Any]:
        """Get contents of a file or directory from repository.

        Args:
            repo_path: Path to the repository
            resource_path: Path to the resource within the repository

        Returns:
            Dict containing resource information and contents
        """
        repo = await self.repo_manager.get_repository(repo_path)
        return await repo.get_resource(resource_path)
