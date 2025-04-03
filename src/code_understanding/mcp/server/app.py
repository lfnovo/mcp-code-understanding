"""
Core MCP server implementation using FastMCP.
"""
import logging
import sys
import asyncio
import click
from typing import Optional

from mcp.server.fastmcp import FastMCP
from code_understanding.config import Config, load_config
from code_understanding.repository import RepositoryManager
from code_understanding.context import ContextGenerator
from code_understanding.qa import QAEngine

# Configure logging
logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("code_understanding.mcp")

def create_mcp_server(config: Optional[Config] = None) -> FastMCP:
    """Create and configure the MCP server instance"""
    if config is None:
        config = load_config()
    
    server = FastMCP(
        name=config.server.name,
        host=config.server.host,
        port=config.server.port
    )
    
    # Initialize core components
    repo_manager = RepositoryManager(config.repositories)
    context_generator = ContextGenerator(config.context)
    qa_engine = QAEngine()
    
    # Register tools
    register_tools(server, repo_manager, context_generator, qa_engine)
    
    return server

def register_tools(
    mcp_server: FastMCP,
    repo_manager: RepositoryManager,
    context_generator: ContextGenerator,
    qa_engine: QAEngine
) -> None:
    """Register all MCP tools with the server."""
    
    @mcp_server.tool(
        name="get_context",
        description="Generate and return structured context about a repository"
    )
    async def get_context(repo_path: str) -> dict:
        """Generate and return structured context about a repository."""
        repo = await repo_manager.get_repository(repo_path)
        return await context_generator.generate_context(repo)
    
    @mcp_server.tool(
        name="get_resource",
        description="Retrieve specific files or directory listings"
    )
    async def get_resource(repo_path: str, resource_path: str) -> dict:
        """Retrieve specific files or directory listings."""
        repo = await repo_manager.get_repository(repo_path)
        return await repo.get_resource(resource_path)
    
    @mcp_server.tool(
        name="answer_question",
        description="Answer natural language questions about code"
    )
    async def answer_question(repo_path: str, question: str) -> dict:
        """Answer natural language questions about code."""
        repo = await repo_manager.get_repository(repo_path)
        return await qa_engine.answer_question(repo, question)
    
    @mcp_server.tool(
        name="refresh_repo",
        description="Update a remote repository with latest changes"
    )
    async def refresh_repo(repo_path: str) -> dict:
        """Update a remote repository with latest changes."""
        return await repo_manager.refresh_repository(repo_path)
    
    @mcp_server.tool(
        name="clone_repo",
        description="Clone a new remote repository"
    )
    async def clone_repo(url: str, branch: Optional[str] = None) -> dict:
        """Clone a new remote repository."""
        return await repo_manager.clone_repository(url, branch)

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
