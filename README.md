# Code Understanding MCP Server

An MCP (Model Context Protocol) server designed to understand codebases and provide intelligent context to AI coding assistants. This server handles both local and remote GitHub repositories and supports standard MCP-compliant operations.

## Features

- **Repository Management**
  - Support for both local and remote Git repositories
  - Efficient repository caching system
  - Automatic background analysis of cloned repositories
  - Repository refresh capabilities to stay in sync with source

- **Code Analysis**
  - Semantic analysis of code structure and relationships
  - Critical file identification using complexity metrics
  - Directory structure analysis
  - Documentation discovery and categorization
  - Support for targeted analysis of specific files/directories

- **Resource Management**
  - Configurable repository cache limits
  - Token-aware analysis for large codebases
  - Background processing for intensive operations
  - Progress tracking for long-running tasks

## Prerequisites

- **Python 3.11 or 3.12**: Required for both development and usage
  ```bash
  # Verify your Python version
  python --version
  # or
  python3 --version
  ```
- **UV Package Manager**: The modern Python package installer
  ```bash
  # Install UV
  curl -sSf https://astral.sh/uv/install.sh | sh
  ```

## Installation

### For End Users

Install and run the application globally:

```bash
# Install the package globally
uv pip install --system mcp-code-understanding

# Run the application
mcp-code-understanding
```

### For Developers

To contribute or run this project locally:

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/mcp-code-understanding.git
cd mcp-code-understanding

# 2. Create virtual environment
uv venv

# 3. Install dependencies (editable mode with dev extras)
uv pip install -e ".[dev]"

# 4. Activate virtual environment
source .venv/bin/activate

# 5. Run tests
pytest

# 6. Run the application
mcp-code-understanding
```

## Configuration

### Base Configuration

The server uses a `config.yaml` file for base configuration. This file is automatically created in the standard configuration directory (`~/.config/mcp-code-understanding/config.yaml`) when the server first runs. You can also place a `config.yaml` file in your current directory to override the default configuration.

Here's the default configuration structure:

```yaml
name: "Code Understanding Server"
log_level: "debug"

repository:
  cache_dir: "~/.cache/mcp-code-understanding"
  max_cached_repos: 2

documentation:
  include_tags:
    - markdown
    - rst
    - adoc
  include_extensions:
    - .md
    - .markdown
    - .rst
    - .txt
    - .adoc
    - .ipynb
  format_mapping:
    tag:markdown: markdown
    tag:rst: restructuredtext
    tag:adoc: asciidoc
    ext:.md: markdown
    ext:.markdown: markdown
    ext:.rst: restructuredtext
    ext:.txt: plaintext
    ext:.adoc: asciidoc
    ext:.ipynb: jupyter
  category_patterns:
    readme: 
      - readme
    api: 
      - api
    documentation:
      - docs
      - documentation
    examples:
      - examples
      - sample
```

### GitHub Authentication

GitHub authentication is handled exclusively through environment variables. Set your GitHub Personal Access Token using:

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="your-token-here"
```

## MCP Tools and Usage

The server provides the following MCP tools for code understanding:

### 1. Repository Management

#### clone_repo
Clones a repository and builds a comprehensive repository map in the background. This map is a critical component that:
- Analyzes and indexes all source files
- Extracts function signatures, class definitions, and their relationships
- Maps the codebase structure and dependencies
- Enables semantic understanding of the code

This background analysis is essential for all other analysis tools to function properly.

```python
response = await clone_repo(
    url="https://github.com/user/repo",  # Repository URL or local path
    branch="main"  # Optional: specific branch
)
```

#### refresh_repo
Updates a previously cloned repository with latest changes and triggers a complete rebuild of the repository map:
```python
response = await refresh_repo(
    repo_path="https://github.com/user/repo"  # Original repo URL/path
)
```

### 2. Code Analysis

#### get_source_repo_map
Retrieves the repository map that was built during `clone_repo` or `refresh_repo`. This map contains the semantic analysis of your code's structure, including function signatures, class hierarchies, and code relationships:
```python
response = await get_source_repo_map(
    repo_path="https://github.com/user/repo",
    files=["src/main.py"],  # Optional: specific files
    directories=["src/"],    # Optional: specific directories
    max_tokens=10000        # Optional: limit response size
)
```

#### get_repo_structure
Analyzes repository directory structure:
```python
response = await get_repo_structure(
    repo_path="https://github.com/user/repo",
    directories=["src/"],    # Optional: limit to directories
    include_files=True      # Optional: include file listings
)
```

#### get_repo_critical_files
Identifies structurally significant files:
```python
response = await get_repo_critical_files(
    repo_path="https://github.com/user/repo",
    files=None,             # Optional: specific files
    directories=None,       # Optional: specific directories
    limit=50,              # Optional: max results
    include_metrics=True   # Optional: include detailed metrics
)
```

#### get_repo_file_content
Retrieves file contents or directory listings:
```python
response = await get_repo_file_content(
    repo_path="https://github.com/user/repo",
    resource_path="src/main.py"
)
```

#### get_repo_documentation
Analyzes repository documentation:
```python
response = await get_repo_documentation(
    repo_path="https://github.com/user/repo"
)
```

### Response Handling

Most tools return responses with a consistent structure:
```python
{
    "status": str,     # "success", "pending", "building", "error"
    "content": dict,   # Tool-specific response data
    "message": str,    # Optional status/error message
    "metadata": dict   # Optional processing metadata
}
```

### Best Practices

1. **Repository Analysis Flow**:
   - Start with `clone_repo` for initial setup
   - Use `get_repo_structure` to understand codebase organization
   - Identify key files with `get_repo_critical_files`
   - Get detailed analysis with `get_source_repo_map`
   - Access documentation with `get_repo_documentation`

2. **Large Repository Handling**:
   - Use directory/file filtering to analyze specific parts
   - Set appropriate `max_tokens` limits
   - Consider using `refresh_repo` for incremental updates
   - Monitor status responses for long-running operations

3. **Resource Management**:
   - Configure `max_cached_repos` based on available storage
   - Clean up unused repositories periodically
   - Use targeted analysis for large codebases

## Server Configuration

When running the MCP server, several command-line options are available:

```bash
mcp-code-understanding [OPTIONS]

Options:
  --port INTEGER            Port to listen on for SSE (default: 3001)
  --transport [stdio|sse]   Transport type (default: stdio)
  --cache-dir TEXT         Directory to store repository cache
  --max-cached-repos INT   Maximum number of cached repositories
  --help                   Show this message and exit
```

## Development

Run tests:
```bash
uv venv run pytest
```

Format code:
```bash
uv venv run black .
uv venv run isort .
```

Type checking:
```bash
uv venv run mypy .
```

## License

MIT