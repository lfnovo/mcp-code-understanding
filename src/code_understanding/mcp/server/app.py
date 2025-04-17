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
        name="get_repo_file_content",
        description="Retrieve file contents or directory listings from a repository. For files, returns the complete file content. For directories, returns a non-recursive listing of immediate files and subdirectories.",
    )
    async def get_repo_file_content(repo_path: str, resource_path: str) -> dict:
        """
        Retrieve file contents or directory listings from a repository.

        Args:
            repo_path (str): Path or URL to the repository
            resource_path (str): Path to the target file or directory within the repository

        Returns:
            dict: For files:
                {
                    "type": "file",
                    "path": str,  # Relative path within repository
                    "content": str  # Complete file contents
                }
                For directories:
                {
                    "type": "directory",
                    "path": str,  # Relative path within repository
                    "contents": List[str]  # List of immediate files and subdirectories
                }

        Note:
            Directory listings are not recursive - they only show immediate contents.
            To explore subdirectories, make additional calls with the subdirectory path.
        """
        try:
            repo = await repo_manager.get_repository(repo_path)
            return await repo.get_resource(resource_path)
        except Exception as e:
            logger.error(f"Error getting resource: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    @mcp_server.tool(
        name="refresh_repo",
        description="Update a previously cloned repository in MCP's cache with latest changes and trigger reanalysis. Use this to ensure analysis is based on latest code.",
    )
    async def refresh_repo(repo_path: str) -> dict:
        """
        Update a previously cloned repository in MCP's cache and refresh its analysis.

        For Git repositories, performs a git pull to get latest changes. Then triggers
        a new repository map build to ensure all analysis is based on the updated code.

        Args:
            repo_path (str): Path or URL matching what was originally provided to clone_repo

        Returns:
            dict: Response with format:
                {
                    "status": str,  # "success", "error", or "not_git_repo"
                    "commit": str,  # (On success) Hash of the latest commit
                    "error": str    # (On error) Error message
                }

        Note:
            - This is a setup operation for MCP analysis only
            - Updates MCP's cached copy, does not modify the source repository
            - Automatically triggers rebuild of repository map with updated files
            - For non-Git repositories, returns {"status": "not_git_repo"}
        """
        try:
            return await repo_manager.refresh_repository(repo_path)
        except Exception as e:
            logger.error(f"Error refreshing repository: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    @mcp_server.tool(
        name="clone_repo",
        description="Clone a repository into the MCP server's analysis cache and initiate background analysis. Required before using other analysis endpoints like get_source_repo_map.",
    )
    async def clone_repo(url: str, branch: str = None) -> dict:
        """
        Clone a repository into MCP server's cache and prepare it for analysis.

        This tool must be called before using analysis endpoints like get_source_repo_map
        or get_repo_documentation. It copies the repository into MCP's cache and
        automatically starts building a repository map in the background.

        Args:
            url (str): URL of remote repository or path to local repository to analyze
            branch (str, optional): Specific branch to clone for analysis

        Returns:
            dict: Response with format:
                {
                    "status": "pending",
                    "path": str,  # Cache location where repo is being cloned
                    "message": str  # Status message about clone and analysis
                }

        Note:
            - This is a setup operation for MCP analysis only
            - Does not modify the source repository
            - Repository map building starts automatically after clone completes
            - Use get_source_repo_map to check analysis status and retrieve results
        """
        try:
            logger.debug(f"[TRACE] clone_repo: Starting get_repository for {url}")
            repo = await repo_manager.get_repository(url)
            logger.debug(f"[TRACE] clone_repo: get_repository completed for {url}")

            # Note: RepoMap build will be started automatically after clone completes
            response = {
                "status": "pending",
                "path": str(repo.root_path),
                "message": "Repository clone started in background",
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
        name="get_source_repo_map",
        description="Retrieve a semantic analysis map of the repository's source code structure, including file hierarchy, functions, classes, and their relationships. Repository must be previously cloned via clone_repo.",
    )
    async def get_source_repo_map(
        repo_path: str,
        files: List[str] = None,
        directories: List[str] = None,
        max_tokens: int = None,
    ) -> dict:
        """
        Retrieve a semantic analysis map of the repository's code structure.

        Returns a detailed map of the repository's structure, including file hierarchy,
        code elements (functions, classes, methods), and their relationships. Can analyze
        specific files/directories or the entire repository.

        Args:
            repo_path (str): Path or URL matching what was originally provided to clone_repo
            files (List[str], optional): Specific files to analyze. If None, analyzes all files
            directories (List[str], optional): Specific directories to analyze. If None, analyzes all directories
            max_tokens (int, optional): Limit total tokens in analysis. Useful for large repositories

        Returns:
            dict: Response with format:
                {
                    "status": str,  # "success", "building", "waiting", or "error"
                    "content": str,  # Hierarchical representation of code structure
                    "metadata": {    # Analysis metadata
                        "excluded_files_by_dir": dict,
                        "is_complete": bool,
                        "max_tokens": int
                    },
                    "message": str,  # Present for "building"/"waiting" status
                    "error": str     # Present for "error" status
                }

        Note:
            - Repository must be previously cloned using clone_repo
            - Initial analysis happens in background after clone
            - Returns "building" status while analysis is in progress
            - Content includes file structure, code elements, and their relationships
            - For large repos, consider using max_tokens or targeting specific directories
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

    @mcp_server.tool(
        name="get_repo_documentation",
        description="Retrieve and analyze documentation files from a repository, including README files, API docs, design documents, and other documentation. Repository must be previously cloned via clone_repo.",
    )
    async def get_repo_documentation(repo_path: str) -> dict:
        """
        Retrieve and analyze repository documentation files.

        Searches for and analyzes documentation within the repository, including:
        - README files
        - API documentation
        - Design documents
        - User guides
        - Installation instructions
        - Other documentation files

        Args:
            repo_path (str): Path or URL matching what was originally provided to clone_repo

        Returns:
            dict: Currently returns a stub response as feature is under development:
                {
                    "status": "pending",
                    "message": str  # Information about feature status
                }

        Note:
            - Repository must be previously cloned using clone_repo
            - Will support various documentation formats (markdown, rst, etc.)
            - Will provide structured access to repository documentation
            - Currently under development
        """
        return {
            "status": "pending",
            "message": "This endpoint is under construction. Documentation retrieval will be implemented soon.",
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
