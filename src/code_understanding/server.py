"""
Core MCP server implementation using FastMCP.
"""

from pathlib import Path
from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP
import yaml

from .config import Config, load_config
from .repository import RepositoryManager
from .context import ContextGenerator
from .qa import QAEngine


class CodeUnderstandingServer:
    def __init__(self, config_path: Optional[Path] = None):
        self.config = load_config(config_path)
        self.mcp_server = FastMCP(name=self.config.server.name)

        # Initialize core components
        self.repo_manager = RepositoryManager(self.config.repositories)
        self.context_generator = ContextGenerator(self.config.context)
        self.qa_engine = QAEngine()

        # Register MCP tools
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tools with the server."""

        @self.mcp_server.tool()
        async def get_context(repo_path: str) -> Dict[str, Any]:
            """Generate and return structured context about a repository."""
            repo = await self.repo_manager.get_repository(repo_path)
            return await self.context_generator.generate_context(repo)

        @self.mcp_server.tool()
        async def get_resource(repo_path: str, resource_path: str) -> Dict[str, Any]:
            """Retrieve specific files or directory listings."""
            repo = await self.repo_manager.get_repository(repo_path)
            return await repo.get_resource(resource_path)

        @self.mcp_server.tool()
        async def answer_question(repo_path: str, question: str) -> Dict[str, str]:
            """Answer natural language questions about code."""
            repo = await self.repo_manager.get_repository(repo_path)
            return await self.qa_engine.answer_question(repo, question)

        @self.mcp_server.tool()
        async def refresh_repo(repo_path: str) -> Dict[str, Any]:
            """Update a remote repository with latest changes."""
            return await self.repo_manager.refresh_repository(repo_path)

        @self.mcp_server.tool()
        async def clone_repo(url: str, branch: Optional[str] = None) -> Dict[str, Any]:
            """Clone a new remote repository."""
            return await self.repo_manager.clone_repository(url, branch)

    async def start(self):
        """Start the MCP server."""
        await self.mcp_server.start()

    async def stop(self):
        """Stop the MCP server and cleanup resources."""
        await self.mcp_server.stop()
        await self.repo_manager.cleanup()


def main():
    """Entry point for running the server."""
    import asyncio

    server = CodeUnderstandingServer()
    asyncio.run(server.start())
