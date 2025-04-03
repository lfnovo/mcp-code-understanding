# MCP Server Architecture Specification

## Overview

This document specifies the architecture for a modular, extensible MCP (Model Context Protocol) server designed to understand codebases and provide intelligent context to AI coding assistants. The server handles both local and remote GitHub repositories and supports standard MCP-compliant operations.

> **MVP Scope Note**: For the initial MVP, we will defer implementation of Vector Store and LLMLingua integration, but will architect the system to allow for clean injection of these capabilities in the future.

## MCP Implementation

This server will be implemented using the official Python MCP SDK, specifically using the FastMCP high-level interface:

* **Official repository**: [github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)
* **Package name**: `mcp` (not the deprecated `fastmcp` package)
* **Key module**: `mcp.server.fastmcp`

## System Components

### 1. MCP Server (FastMCP)

**Purpose**: Core server component that handles the MCP protocol implementation.

**Implementation**:
- Uses the official MCP Python SDK's FastMCP class
- Manages server lifecycle, tool registration, and resource handling
- Handles both stdio and SSE transports automatically

**Key Concepts**:
- The FastMCP class from `mcp.server.fastmcp` module provides a high-level interface
- Server object registration follows MCP guidelines
- Transport handling is managed internally by the SDK
- Tool and resource registration uses Python decorators

**Reference Documentation**:
- Main FastMCP class documentation in the [python-sdk repository](https://github.com/modelcontextprotocol/python-sdk)
- Transport protocols defined in the [MCP specification](https://spec.modelcontextprotocol.io)

### 2. Repository Manager

**Purpose**: Handle repository operations for both local and remote repositories.

**Implementation**:
- Local repository detection and scanning
- GitHub API integration for remote repositories
- Caching and refreshing strategies

**Key Responsibilities**:
- Detect and manage local repositories
- Clone, cache, and update remote GitHub repositories
- Provide a unified interface for accessing repository contents
- Handle repository metadata and state tracking

**Integration with GitPython**:
- Use GitPython for Git operations (clone, pull, etc.)
- Reference the [GitPython documentation](https://gitpython.readthedocs.io/)
- Implement appropriate error handling for Git operations

**Repository Caching Strategy**:
- Cache remote repositories with unique identifiers
- Implement configurable refresh intervals
- Track metadata including last update time and source URL

### 3. Context Generator

**Purpose**: Analyze repositories to generate structured context for AI assistants.

**Implementation**:
- Pipeline architecture for extensibility
- Language-specific parsers for different file types
- Project structure analysis and tech stack detection

**Key Responsibilities**:
- Parse code files by language type
- Extract structural information (classes, functions, imports)
- Detect frameworks, libraries, and dependencies
- Generate summaries at file and project level
- Format output for consumption by AI assistants

**Parser Integration**:
- Consider Tree-sitter for robust code parsing
- Reference the [Tree-sitter Python bindings](https://github.com/tree-sitter/py-tree-sitter)
- Implement language-specific parsers using a common interface

**Analysis Pipeline**:
- Design as a series of modular analyzers that can be composed
- Each analyzer focuses on a specific aspect (dependencies, entry points, etc.)
- Results are aggregated into a comprehensive context object

### 4. Q&A Engine

**Purpose**: Answer natural language questions about the codebase.

**Implementation**:
- Integration with LangChain for retrieval-based QA
- Pluggable retriever interface for different search strategies
- Query processing pipeline

**Key Responsibilities**:
- Process natural language questions about code
- Retrieve relevant code sections and documentation
- Format responses with source references
- Handle context limitations and query complexity

**LangChain Integration**:
- Use LangChain's document processing capabilities
- Reference [LangChain's GitHub](https://github.com/langchain-ai/langchain)
- Implement document chunking and retrieval without vector embeddings for MVP

**Retriever Interface**:
- Design a common interface for content retrieval strategies
- Implement a simple keyword-based retriever for MVP
- Design the interface to allow future vector-based retrievers

### 5. MCP Tool Registry

**Purpose**: Implement MCP tools that expose functionality to clients.

**Implementation**:
- Register tools with FastMCP using decorators
- Define parameter types and documentation
- Implement tool handlers that coordinate other components

**Key Tool Concepts**:
- Tools are registered using the `@mcp.tool()` decorator
- Parameter types are inferred from type annotations
- Return types determine how results are presented to the client
- Documentation strings are used to describe tool functionality

**Required Tools**:
1. **get_context**: Generate and return structured context about a repository
2. **get_resource**: Retrieve specific files or directory listings
3. **answer_question**: Answer natural language questions about code
4. **refresh_repo**: Update a remote repository with latest changes
5. **clone_repo**: Clone a new remote repository

**Tool Registration**:
- Reference the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) for tool registration patterns
- Use proper type annotations for automatic schema generation
- Provide clear documentation strings for each tool

## Extension Points (Post-MVP)

For the MVP, we'll define interfaces for future extensions to ensure clean integration later.

### Future Vector Store Integration

While the MVP will not include vector store capabilities, we'll architect the system to allow for future integration.

**Key Design Principles**:
- Define a common `Retriever` interface for all content retrieval strategies
- Implement a simple keyword-based retriever for the MVP
- Design the interface to accommodate vector-based retrievers in the future
- Ensure the Q&A engine can work with any retriever implementation

**Integration Path**:
- The interface should define standard methods like `retrieve()` and `index()`
- Future vector retrievers will implement this same interface
- Reference retrieval patterns from [LangChain retrievers](https://python.langchain.com/docs/modules/data_connection/retrievers/) for implementation guidance

### Future LLMLingua Integration

The MVP will not include LLMLingua compression, but we'll design extension points for future integration.

**Key Design Principles**:
- Implement a pipeline architecture for context generation
- Define a `ContextProcessor` interface for pipeline stages
- Allow processors to be added, removed, or reordered
- Design the context data structure to be compatible with compression

**Integration Path**:
- Future LLMLingua integration will be implemented as a processor in the pipeline
- No changes to other components should be needed when adding compression
- Keep context generation and compression as separate concerns

## Configuration

The server supports the following configuration options:

```yaml
# Server configuration
server:
  name: "Code Understanding Server"
  log_level: "info"
  dependencies:
    - "gitpython"
    - "langchain"
    - "tree-sitter"

# Repository configuration
repositories:
  cache_dir: "./repo_cache"
  refresh_interval: 3600  # seconds
  github:
    api_token: "${GITHUB_TOKEN}"

# Context generation
context:
  summary_depth: "medium"  # basic, medium, detailed
  include_dependencies: true
  max_files_per_context: 100

# Future extensions (not used in MVP, but config structure prepared)
extensions:
  llmlingua:
    enabled: false  # Will be false for MVP
  vector_store:
    enabled: false  # Will be false for MVP
```

**Configuration Management**:
- FastMCP handles server configuration and dependencies
- Environment variables can be passed during installation
- Reference the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) for configuration options

**Dependency Management**:
- Dependencies specified in the FastMCP constructor are installed automatically
- Use the `dependencies` parameter to specify required packages
- Environment-specific configuration can be provided at install time

## Data Flow

1. **Client Request Flow**:
   - Client sends request to MCP server via stdio or SSE
   - MCP Python SDK handles protocol details and routes to appropriate handler
   - Tool or resource handler processes the request
   - Response flows back through MCP SDK to client

2. **Repository Processing Flow**:
   - Repository is cloned/detected and cached if needed
   - Files are parsed by language-specific parsers
   - Code analyzers process parsed files
   - Context generator creates structured context
   - Context is returned to the client (compression deferred to post-MVP)

3. **Q&A Flow**:
   - Question received from client through the `answer_question` tool
   - Query is analyzed to determine intent and information needs
   - Keyword-based retriever finds relevant context (vector retrieval deferred to post-MVP)
   - Answer is generated using the retrieved context
   - References to source files are included in the response

## Deployment

The MCP server can be deployed in several ways using the MCP Python SDK tools:

1. **Development Mode**:
   ```bash
   mcp dev server.py
   ```
   This launches the MCP Inspector web interface for interactive testing.

2. **Claude Desktop Integration**:
   ```bash
   mcp install server.py
   ```
   This installs the server in Claude Desktop for regular use.

3. **Direct Execution**:
   ```bash
   python server.py
   # or
   mcp run server.py
   ```
   This runs the server directly, handling both stdio and SSE protocols.

## Implementation Roadmap

1. **Phase 1: Core Functionality (Current MVP)**
   - Set up MCP server using the official Python SDK
   - Implement local repository handling
   - Create basic context generation pipeline
   - Add README generation capabilities

2. **Phase 2: Remote Repositories (Current MVP)**
   - Implement GitHub API integration with GitPython
   - Develop repository caching strategy
   - Add repository refresh mechanisms

3. **Phase 3: Advanced Analysis (Current MVP)**
   - Create language-specific parsers
   - Implement dependency analysis
   - Add tech stack detection
   - Develop basic Q&A capabilities without vector storage

4. **Future Phase: Extensions (Post-MVP)**
   - Integrate vector store capabilities
   - Add LLMLingua compression
   - Enhance retrieval-based Q&A functionality

## Technical Implementation Guide

### Official MCP SDK References

For accurate implementation, refer to these authoritative sources:

- **Official Python MCP SDK**: [github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)
- **PyPI Package**: [pypi.org/project/mcp/](https://pypi.org/project/mcp/)
- **Protocol Specification**: [spec.modelcontextprotocol.io](https://spec.modelcontextprotocol.io)
- **MCP Documentation**: [modelcontextprotocol.io](https://modelcontextprotocol.io)

When implementing the server, consult these resources for the correct patterns rather than relying on generated code examples.

### Key External Dependencies

- **MCP Python SDK**: For MCP server implementation (`pip install "mcp[cli]"`)
- **GitPython**: For repository management
- **Tree-sitter**: For code parsing (optional)
- **PyGithub**: For GitHub API integration
- **LangChain**: For basic Q&A capabilities (non-vector based for MVP)

### Implementation Structure

The server will be structured around these key components, following the FastMCP architecture:

1. **MCP Server**: Central FastMCP instance that defines tools, resources, and server configuration
2. **Repository Manager**: Component to handle local and remote repository operations
3. **Context Generator**: Pipeline for creating structured code context
4. **Tool Registry**: Collection of MCP tools exposing functionality to clients

### Extension Points

The architecture should define clean interfaces for future extensions:

1. **Retriever Interface**: Abstract base class for content retrieval strategies
2. **Context Processing Pipeline**: Modular pipeline allowing for future processors:

```python
# Installation
# pip install fastmcp

from fastmcp import Server
import asyncio
import json
import sys

# Create a FastMCP server instance
server = Server()

# Register tools with the server
@server.tool(
    name="get_context",
    description="Return structured summary or doc for code understanding",
)
async def get_context(repo_id: str, options: dict = None) -> dict:
    # Implementation goes here
    pass

# Set up stdio transport
async def stdio_transport():
    # Read from stdin and write to stdout according to JSON-RPC 2.0
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, asyncio.get_event_loop())
    
    while True:
        line = await reader.readline()
        if not line:
            break
            
        request = json.loads(line)
        response = await server.handle_jsonrpc(request)
        writer.write(json.dumps(response).encode() + b'\n')
        await writer.drain()

# Set up SSE/HTTP transport
async def setup_http_server(host="localhost", port=8080):
    from aiohttp import web
    import json
    
    app = web.Application()
    
    async def handle_sse(request):
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        await response.prepare(request)
        
        # Process the JSON-RPC request from the body
        body = await request.json()
        result = await server.handle_jsonrpc(body)
        
        # Send the response as an SSE event
        await response.write(f"data: {json.dumps(result)}\n\n".encode())
        await response.write(b"event: end\ndata: end\n\n")
        
        return response
    
    app.router.add_post('/mcp', handle_sse)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"HTTP server started at http://{host}:{port}")

# Main entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Server")
    parser.add_argument("--http", action="store_true", help="Run as HTTP server")
    parser.add_argument("--host", default="localhost", help="HTTP server host")
    parser.add_argument("--port", type=int, default=8080, help="HTTP server port")
    args = parser.parse_args()
    
    if args.http:
        asyncio.run(setup_http_server(args.host, args.port))
    else:
        asyncio.run(stdio_transport())
```

### Implementing Repository Manager

GitPython is used for repository management:

```python
# Installation
# pip install GitPython

import os
import git
from pathlib import Path
import hashlib

class RepositoryManager:
    def __init__(self, cache_dir="./repo_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.repositories = {}  # Cache of loaded repositories
    
    def _get_repo_hash(self, url):
        """Generate a unique identifier for a repository URL."""
        return hashlib.sha256(url.encode()).hexdigest()
    
    def detect_local_repo(self, path):
        """Detect and load a local repository."""
        path = Path(path).absolute()
        repo_id = f"local:{path}"
        
        if repo_id not in self.repositories:
            # Check if this is a git repository
            try:
                git_repo = git.Repo(path)
                is_git = True
            except git.InvalidGitRepositoryError:
                is_git = False
            
            # Create repository object
            repo = Repository(
                repo_id=repo_id,
                root_path=path,
                repo_type="local",
                is_git=is_git
            )
            self.repositories[repo_id] = repo
            
        return self.repositories[repo_id]
    
    async def clone_remote_repo(self, url, branch="main"):
        """Clone a remote repository."""
        repo_hash = self._get_repo_hash(url)
        repo_path = self.cache_dir / repo_hash
        repo_id = f"remote:{repo_hash}"
        
        if repo_id in self.repositories:
            return self.repositories[repo_id]
        
        if not repo_path.exists():
            # Clone the repository
            git.Repo.clone_from(url, repo_path, branch=branch)
        
        # Create repository object
        repo = Repository(
            repo_id=repo_id,
            root_path=repo_path,
            repo_type="remote",
            is_git=True,
            url=url,
            branch=branch
        )
        self.repositories[repo_id] = repo
        
        return repo
    
    async def refresh_repo(self, repo_id):
        """Refresh a repository (pull latest changes)."""
        if repo_id not in self.repositories:
            return False
        
        repo = self.repositories[repo_id]
        if repo.repo_type != "remote" or not repo.is_git:
            return False
        
        try:
            git_repo = git.Repo(repo.root_path)
            git_repo.remotes.origin.pull()
            return True
        except Exception as e:
            print(f"Error refreshing repository: {e}")
            return False
    
    def get_repository(self, repo_id):
        """Get a repository by ID."""
        return self.repositories.get(repo_id)

class Repository:
    def __init__(self, repo_id, root_path, repo_type, is_git, url=None, branch=None):
        self.id = repo_id
        self.root_path = Path(root_path)
        self.repo_type = repo_type
        self.is_git = is_git
        self.url = url
        self.branch = branch
    
    def get_file_content(self, file_path):
        """Get content of a file in the repository."""
        path = self.root_path / file_path
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return path.read_text(errors="replace")
    
    def list_files(self, pattern=None):
        """List files in the repository, optionally filtered by pattern."""
        import glob
        
        if pattern:
            return [str(path.relative_to(self.root_path)) 
                   for path in self.root_path.glob(pattern)
                   if path.is_file()]
        else:
            result = []
            for root, _, files in os.walk(self.root_path):
                root_path = Path(root)
                for file in files:
                    file_path = root_path / file
                    result.append(str(file_path.relative_to(self.root_path)))
            return result
```

### Implementing Context Generator

```python
class ContextGenerator:
    def __init__(self, parsers=None, analyzers=None):
        self.parsers = parsers or []
        self.analyzers = analyzers or []
    
    async def generate_context(self, repo, options=None):
        """Generate context for a repository."""
        options = options or {}
        
        # Parse files
        parsed_files = []
        for file_path in repo.list_files():
            # Skip files based on options
            if options.get('exclude_patterns'):
                if any(file_path.endswith(pattern) for pattern in options['exclude_patterns']):
                    continue
                    
            try:
                content = repo.get_file_content(file_path)
                parser = self._find_parser(file_path)
                if parser:
                    parsed_file = await parser.parse_file(content, file_path)
                    parsed_files.append(parsed_file)
            except Exception as e:
                print(f"Error parsing file {file_path}: {e}")
        
        # Run analyzers
        results = {}
        for analyzer in self.analyzers:
            try:
                result = await analyzer.analyze(repo, parsed_files)
                results.update(result)
            except Exception as e:
                print(f"Error running analyzer {analyzer.__class__.__name__}: {e}")
        
        # Prepare final context
        context = {
            "repo_id": repo.id,
            "repo_type": repo.repo_type,
            "file_count": len(parsed_files),
            "language_summary": self._get_language_summary(parsed_files),
            "analysis_results": results,
            "generated_at": datetime.datetime.now().isoformat(),
        }
        
        # Here is where we would inject LLMLingua compression in the future
        
        return context
    
    def _find_parser(self, file_path):
        """Find a parser that can handle this file."""
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser
        return None
    
    def _get_language_summary(self, parsed_files):
        """Get summary of languages used in the repository."""
        languages = {}
        for file in parsed_files:
            lang = file.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
        return languages

# Example parser for Python files
class PythonParser:
    def can_parse(self, file_path):
        return file_path.endswith(".py")
    
    async def parse_file(self, content, file_path):
        # In a real implementation, you would use AST or tree-sitter here
        import ast
        
        try:
            tree = ast.parse(content)
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            
            return {
                "path": file_path,
                "language": "python",
                "classes": classes,
                "functions": functions,
                "imports": self._extract_imports(tree),
                "size_bytes": len(content),
            }
        except SyntaxError:
            # Fall back to basic info if parsing fails
            return {
                "path": file_path,
                "language": "python",
                "size_bytes": len(content),
                "parse_error": True
            }
    
    def _extract_imports(self, tree):
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for name in node.names:
                    imports.append(f"{module}.{name.name}")
        return imports

# Example analyzer for tech stack detection
class TechStackAnalyzer:
    async def analyze(self, repo, parsed_files):
        # This is a simplified example - a real implementation would be more sophisticated
        tech_stack = {
            "languages": set(),
            "frameworks": set(),
            "databases": set(),
            "tools": set(),
        }
        
        # Extract languages
        for file in parsed_files:
            if "language" in file:
                tech_stack["languages"].add(file["language"])
        
        # Look for frameworks and databases in imports
        for file in parsed_files:
            if file.get("language") == "python" and "imports" in file:
                for imp in file.get("imports", []):
                    if any(fw in imp.lower() for fw in ["django", "flask", "fastapi", "tornado"]):
                        tech_stack["frameworks"].add(imp.split(".")[0])
                    if any(db in imp.lower() for db in ["sqlite", "postgres", "mysql", "mongodb"]):
                        tech_stack["databases"].add(imp.split(".")[0])
        
        # Check for configuration files
        file_paths = [file.get("path") for file in parsed_files]
        if any("docker" in path.lower() for path in file_paths):
            tech_stack["tools"].add("docker")
        if any("kubernetes" in path.lower() for path in file_paths):
            tech_stack["tools"].add("kubernetes")
        
        # Convert sets to lists for JSON serialization
        return {
            "tech_stack": {
                key: list(value) for key, value in tech_stack.items()
            }
        }
```

### Dependencies

- FastMCP: `pip install fastmcp`
- GitPython: `pip install GitPython`
- aiohttp: `pip install aiohttp` (for HTTP/SSE transport)
- LangChain (for basic Q&A, even without vector stores): `pip install langchain`
- Tree-sitter (optional, for better code parsing): `pip install tree-sitter`
- PyGithub (for GitHub API): `pip install PyGithub`

 8080
   ```

## Project Structure

```
mcp_server/
├── __init__.py
├── main.py                # Entry point
├── config.py              # Configuration handling
├── server/
│   ├── __init__.py
│   ├── mcp_server.py      # FastMCP server implementation
│   ├── stdio.py           # Stdio transport
│   └── http.py            # HTTP/SSE transport
├── repo/
│   ├── __init__.py
│   ├── manager.py         # Repository manager
│   └── repository.py      # Repository class
├── context/
│   ├── __init__.py
│   ├── generator.py       # Context generator
│   ├── pipeline.py        # Processing pipeline
│   ├── parsers/           # Language-specific parsers
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── python.py
│   │   └── javascript.py
│   └── analyzers/         # Code analyzers
│       ├── __init__.py
│       ├── base.py
│       ├── tech_stack.py
│       └── dependencies.py
├── qa/
│   ├── __init__.py
│   ├── engine.py          # Q&A engine
│   └── retriever.py       # Retriever interface and implementations
└── tools/
    ├── __init__.py
    ├── get_context.py     # Tool implementations
    ├── get_resource.py
    ├── answer_question.py
    ├── refresh_repo.py
    └── clone_repo.py
```

## References and Resources

### Official MCP Documentation

- **Model Context Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io/)
- **MCP Specification**: [spec.modelcontextprotocol.io](https://spec.modelcontextprotocol.io/)
- **Python SDK Repository**: [github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)
- **PyPI Package**: [pypi.org/project/mcp/](https://pypi.org/project/mcp/)

### Key Dependencies Documentation

- **GitPython**: [gitpython.readthedocs.io](https://gitpython.readthedocs.io/)
- **LangChain**: [python.langchain.com](https://python.langchain.com/)
- **Tree-sitter**: [tree-sitter.github.io/tree-sitter/](https://tree-sitter.github.io/tree-sitter/)
- **PyGithub**: [pygithub.readthedocs.io](https://pygithub.readthedocs.io/)

### Official MCP Example Servers

For implementation patterns and best practices, refer to the official examples:
- [github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)

---

This architecture specification provides a blueprint for implementing the MCP server for code understanding, focusing on the MVP requirements while enabling future extensibility through clear interfaces and extension points.
