"""
Get repository structure MCP tool implementation.
"""

from typing import Dict, Any, List
from fastmcp import BaseTool


class GetRepoStructureTool(BaseTool):
    """Tool for analyzing repository structure and important files."""

    async def __call__(self, repo_path: str, limit: int) -> List[Dict[str, Any]]:
        """Get sorted list of important files in repository.

        Args:
            repo_path: Path to the repository
            limit: Maximum number of files to return

        Returns:
            List of files with importance scores
        """
        # TODO: Implement using repomap module
        return []
