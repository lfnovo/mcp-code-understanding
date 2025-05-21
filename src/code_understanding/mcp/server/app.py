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
from code_understanding.repository.documentation import get_repository_documentation

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

    server = FastMCP(name=config.name)

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
        description="""Retrieve file contents or directory listings from a repository. For files, returns the complete file content. For directories, returns a non-recursive listing of immediate files and subdirectories.

REQUIRED PARAMETER GUIDANCE:
- repo_path: MUST match the exact format of the original input to clone_repo
  - If you cloned using a GitHub URL (e.g., 'https://github.com/username/repo'), you MUST use that identical URL here
  - If you cloned using a local directory path, you MUST use that identical local path here
  - Mismatched formats will result in 'Repository not found in cache' errors""",
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
        description="""Update a previously cloned repository in MCP's cache with latest changes and trigger reanalysis. Use this to ensure analysis is based on latest code.

REQUIRED PARAMETER GUIDANCE:
- repo_path: MUST match the exact format of the original input to clone_repo
  - If you cloned using a GitHub URL (e.g., 'https://github.com/username/repo'), you MUST use that identical URL here
  - If you cloned using a local directory path, you MUST use that identical local path here
  - Mismatched formats will result in 'Repository not found in cache' errors""",
    )
    async def refresh_repo(repo_path: str) -> dict:
        """
        Update a previously cloned repository in MCP's cache and refresh its analysis.

        For Git repositories, performs a git pull to get latest changes.
        For local directories, copies the latest content from the source.
        Then triggers a new repository map build to ensure all analysis is based on
        the updated code.

        Args:
            repo_path (str): Path or URL matching what was originally provided to clone_repo

        Returns:
            dict: Response with format:
                {
                    "status": str,  # "pending", "error"
                    "path": str,    # (On pending) Cache location being refreshed
                    "message": str, # (On pending) Status message
                    "error": str    # (On error) Error message
                }

        Note:
            - Repository must be previously cloned and have completed initial analysis
            - Updates MCP's cached copy, does not modify the source repository
            - Automatically triggers rebuild of repository map with updated files
            - Operation runs in background, check get_repo_map_content for status
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
        description="""Retrieve a semantic analysis map of the repository's source code structure, including file hierarchy, functions, classes, and their relationships. Repository must be previously cloned via clone_repo.

REQUIRED PARAMETER GUIDANCE:
- repo_path: MUST match the exact format of the original input to clone_repo
  - If you cloned using a GitHub URL (e.g., 'https://github.com/username/repo'), you MUST use that identical URL here
  - If you cloned using a local directory path, you MUST use that identical local path here
  - Mismatched formats will result in 'Repository not found in cache' errors

RESPONSE CHARACTERISTICS:
1. Status Types:
- "threshold_exceeded": Indicates analysis scope exceeds processing limits
- "building": Analysis in progress
- "waiting": Waiting for prerequisite operation
- "success": Analysis complete
- "error": Operation failed

2. Resource Management:
- Repository size impacts processing time and token usage
- 'max_tokens' parameter provides approximate control of response size
    Note: Actual token count may vary slightly above or below specified limit
- File count threshold exists to prevent overload
- Processing time scales with both file count and max_tokens
    Important: Clients should adjust their timeout values proportionally when:
    * Analyzing larger numbers of files
    * Specifying higher max_tokens values
    * Working with complex repositories

3. Scope Control Options:
- 'files': Analyze specific files (useful for targeted analysis)
- 'directories': Analyze specific directories
- Both parameters support gradual exploration of large codebases

4. Response Metadata:
- Contains processing statistics and limitation details
- Provides override_guidance when thresholds are exceeded
- Reports excluded files and completion status

NOTE: This tool supports both broad and focused analysis strategies. Response handling can be adapted based on specific use case requirements and user preferences.""",
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
        name="get_repo_structure",
        description="""Retrieve directory structure and analyzable file counts for a repository to guide analysis decisions.

REQUIRED PARAMETER GUIDANCE:
- repo_path: MUST match the exact format of the original input to clone_repo
  - If you cloned using a GitHub URL (e.g., 'https://github.com/username/repo'), you MUST use that identical URL here
  - If you cloned using a local directory path, you MUST use that identical local path here
  - Mismatched formats will result in 'Repository not found in cache' errors

RESPONSE CHARACTERISTICS:
1. Directory Information:
- Lists directories containing analyzable source code
- Reports number of analyzable files per directory
- Shows directory hierarchy
- Indicates file extensions present in each location

2. Usage:
- Requires repository to be previously cloned via clone_repo
- Helps identify main code directories
- Supports planning targeted analysis
- Shows where analyzable code is located

NOTE: Use this tool to understand repository structure and choose which directories to analyze in detail.""",
    )
    async def get_repo_structure(
        repo_path: str, directories: List[str] = None, include_files: bool = False
    ) -> dict:
        """
        Get repository structure information with optional file listings.

        Args:
            repo_path: Path/URL matching what was provided to clone_repo
            directories: Optional list of directories to limit results to
            include_files: Whether to include list of files in response

        Returns:
            dict: {
                "status": str,
                "message": str,
                "directories": [{
                    "path": str,
                    "analyzable_files": int,
                    "extensions": {
                        "py": 10,
                        "java": 5,
                        "ts": 3
                    },
                    "files": [str]  # Only present if include_files=True
                }],
                "total_analyzable_files": int
            }
        """
        try:
            # Delegate to the RepoMapBuilder service to handle all the details
            return await repo_map_builder.get_repo_structure(
                repo_path, directories=directories, include_files=include_files
            )
        except Exception as e:
            logger.error(f"Error getting repository structure: {e}", exc_info=True)
            return {
                "status": "error",
                "error": f"Failed to get repository structure: {str(e)}",
            }

    @mcp_server.tool(
        name="get_repo_critical_files",
        description="""Identify and analyze the most structurally significant files in a repository to guide code understanding efforts.

REQUIRED PARAMETER GUIDANCE:
- repo_path: MUST match the exact format of the original input to clone_repo
  - If you cloned using a GitHub URL (e.g., 'https://github.com/username/repo'), you MUST use that identical URL here
  - If you cloned using a local directory path, you MUST use that identical local path here
  - Mismatched formats will result in 'Repository not found in cache' errors

RESPONSE CHARACTERISTICS:
1. Analysis Metrics:
   - Calculates importance scores based on:
     * Function count (weight: 2.0)
     * Total cyclomatic complexity (weight: 1.5)
     * Maximum cyclomatic complexity (weight: 1.2)
     * Lines of code (weight: 0.05)
   - Provides detailed metrics per file
   - Ranks files by composite importance score

2. Resource Management:
   - Repository must be previously cloned via clone_repo
   - Analysis performed on-demand using Lizard
   - Efficient for both small and large codebases
   - Supports both full-repo and targeted analysis

3. Scope Control Options:
   - 'files': Analyze specific files
   - 'directories': Analyze specific directories
   - 'limit': Control maximum results returned
   - Default limit of 50 most critical files

4. Response Metadata:
   - Total files analyzed
   - Analysis completion status

NOTE: This tool is designed to guide initial codebase exploration by identifying structurally significant files. Results can be used to target subsequent get_source_repo_map calls for detailed analysis.""",
    )
    async def get_repo_critical_files(
        repo_path: str,
        files: List[str] = None,
        directories: List[str] = None,
        limit: int = 50,
        include_metrics: bool = True,
    ) -> dict:
        """
        Analyze and identify the most structurally significant files in a codebase.

        Uses code complexity metrics to calculate importance scores, helping identify
        files that are most critical for understanding the system's structure.

        Args:
            repo_path: Path/URL matching what was provided to clone_repo
            files: Optional list of specific files to analyze
            directories: Optional list of specific directories to analyze
            limit: Maximum number of files to return (default: 50)
            include_metrics: Include detailed metrics in response (default: True)

        Returns:
            dict: {
                "status": str,  # "success", "error"
                "files": [{
                    "path": str,
                    "importance_score": float,
                    "metrics": {  # Only if include_metrics=True
                        "total_ccn": int,
                        "max_ccn": int,
                        "function_count": int,
                        "nloc": int
                    }
                }],
                "total_files_analyzed": int
            }
        """
        try:
            # Import and initialize the analyzer
            from code_understanding.analysis.complexity import CodeComplexityAnalyzer

            analyzer = CodeComplexityAnalyzer(repo_manager, repo_map_builder)

            # Delegate to the specialized CodeComplexityAnalyzer module
            return await analyzer.analyze_repo_critical_files(
                repo_path=repo_path,
                files=files,
                directories=directories,
                limit=limit,
                include_metrics=include_metrics,
            )
        except Exception as e:
            logger.error(
                f"Unexpected error in get_repo_critical_files: {str(e)}", exc_info=True
            )
            return {
                "status": "error",
                "error": f"An unexpected error occurred: {str(e)}",
            }

    @mcp_server.tool(
        name="get_repo_documentation",
        description="""Retrieve and analyze documentation files from a repository, including README files, API docs, design documents, and other documentation. Repository must be previously cloned via clone_repo.

REQUIRED PARAMETER GUIDANCE:
- repo_path: MUST match the exact format of the original input to clone_repo
  - If you cloned using a GitHub URL (e.g., 'https://github.com/username/repo'), you MUST use that identical URL here
  - If you cloned using a local directory path, you MUST use that identical local path here
  - Mismatched formats will result in 'Repository not found in cache' errors""",
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
            dict: Documentation analysis results with format:
                {
                    "status": str,  # "success", "error", or "waiting"
                    "message": str,  # Only for error/waiting status
                    "documentation": {  # Only for success status
                        "files": [
                            {
                                "path": str,      # Relative path in repo
                                "category": str,  # readme, api, docs, etc.
                                "format": str     # markdown, rst, etc.
                            }
                        ],
                        "directories": [
                            {
                                "path": str,
                                "doc_count": int
                            }
                        ],
                        "stats": {
                            "total_files": int,
                            "by_category": dict,
                            "by_format": dict
                        }
                    }
                }
        """
        try:
            # Call documentation backend module (thin endpoint)
            return await get_repository_documentation(repo_path)
        except Exception as e:
            logger.error(
                f"Error retrieving repository documentation: {e}", exc_info=True
            )
            return {
                "status": "error",
                "message": f"Failed to retrieve repository documentation: {str(e)}",
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
@click.option(
    "--cache-dir",
    help="Directory to store repository cache",
)
@click.option(
    "--max-cached-repos",
    type=int,
    help="Maximum number of cached repositories",
)
def main(
    port: int, transport: str, cache_dir: str = None, max_cached_repos: int = None
) -> int:
    """Run the server with specified transport."""
    try:
        # Create overrides dict from command line args
        overrides = {}
        if cache_dir or max_cached_repos:
            overrides["repository"] = {}
            if cache_dir:
                overrides["repository"]["cache_dir"] = cache_dir
            if max_cached_repos:
                overrides["repository"]["max_cached_repos"] = max_cached_repos

        # Create server with command line overrides
        config = load_config(overrides=overrides)
        
        global server
        server = create_mcp_server(config)

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
