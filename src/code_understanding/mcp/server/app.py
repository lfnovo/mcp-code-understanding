"""
Core MCP server implementation using FastMCP.
"""

import logging
import sys
import asyncio
import click
from typing import List

from mcp.server.fastmcp import FastMCP
from code_understanding.config import ServerConfig, load_config
from code_understanding.repository import RepositoryManager
from code_understanding.context.builder import RepoMapBuilder

# Configure logging
logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("code_understanding.mcp")


def create_mcp_server(config: ServerConfig = None) -> FastMCP:
    """Create and configure the MCP server instance"""
    if config is None:
        config = load_config()

    server = FastMCP(name=config.name, host=config.host, port=config.port)

    # Initialize core components
    repo_manager = RepositoryManager(config.repository)
    repo_map_builder = RepoMapBuilder(cache=repo_manager.cache)

    # Register tools
    register_tools(server, repo_manager, repo_map_builder)

    return server


def register_tools(
    mcp_server: FastMCP,
    repo_manager: RepositoryManager,
    repo_map_builder: RepoMapBuilder,
) -> None:
    """Register all MCP tools with the server."""

    @mcp_server.tool(
        name="get_resource", description="Retrieve specific files or directory listings"
    )
    async def get_resource(repo_path: str, resource_path: str) -> dict:
        """Retrieve specific files or directory listings."""
        try:
            repo = await repo_manager.get_repository(repo_path)
            return await repo.get_resource(resource_path)
        except Exception as e:
            logger.error(f"Error getting resource: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    @mcp_server.tool(
        name="refresh_repo",
        description="Update a remote repository with latest changes",
    )
    async def refresh_repo(repo_path: str) -> dict:
        """Update a remote repository with latest changes."""
        try:
            return await repo_manager.refresh_repository(repo_path)
        except Exception as e:
            logger.error(f"Error refreshing repository: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    @mcp_server.tool(name="clone_repo")
    async def clone_repo(url: str, branch: str = None) -> dict:
        """Clone a repository and start building its RepoMap."""
        try:
            logger.debug(f"[TRACE] clone_repo: Starting get_repository for {url}")
            repo = await repo_manager.get_repository(url)
            logger.debug(f"[TRACE] clone_repo: get_repository completed for {url}")

            # Start RepoMap build asynchronously - this returns immediately
            logger.debug(f"[TRACE] clone_repo: Starting async RepoMap build")
            await repo_map_builder.start_build(str(repo.root_path))
            logger.debug(f"[TRACE] clone_repo: Async RepoMap build started")

            logger.info(
                f"Successfully cloned repository {url} and started RepoMap build"
            )

            response = {
                "status": "success",
                "path": str(repo.root_path),
                "message": "Repository cloned and RepoMap build started",
            }
            logger.debug(
                f"[TRACE] clone_repo: Preparing to return response: {response}"
            )
            return response
        except Exception as e:
            logger.error(f"Error cloning repository: {e}", exc_info=True)
            error_response = {"status": "error", "error": str(e)}
            logger.debug(
                f"[TRACE] clone_repo: Returning error response: {error_response}"
            )
            return error_response

    @mcp_server.tool(
        name="get_context",
        description="Returns RepoMap's semantic analysis of specified files/directories",
    )
    async def get_context(
        repo_path: str,
        files: List[str] = None,
        directories: List[str] = None,
        max_tokens: int = None,
    ) -> dict:
        """
        Returns RepoMap's semantic analysis of specified files/directories.
        Phase 1: Returns full RepoMap output with default metadata values.
        """
        try:
            return await repo_map_builder.get_repo_map_content(
                repo_path, files=files, directories=directories, max_tokens=max_tokens
            )
        except Exception as e:
            logger.error(f"Error getting context: {e}", exc_info=True)
            return {
                "status": "error",
                "error": f"Unexpected error while getting repository context: {str(e)}",
            }


# Create server instance that can be imported by MCP CLI
server = create_mcp_server()


@click.command()
@click.option("--port", default=3001, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type (stdio or sse)",
)
def main(port: int, transport: str) -> int:
    """Run the server with specified transport."""
    try:
        if transport == "stdio":
            asyncio.run(server.run_stdio_async())
        else:
            server.settings.port = port
            asyncio.run(server.run_sse_async())
        return 0
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
