# Code Understanding MCP Server

An MCP (Model Context Protocol) server designed to understand codebases and provide intelligent context to AI coding assistants. This server handles both local and remote GitHub repositories and supports standard MCP-compliant operations.

## Features

- MCP-compliant server implementation using FastMCP
- Local and remote Git repository support
- Code parsing and analysis
- Natural language Q&A about codebases
- Extensible parser architecture

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

Create a `config.yaml` file in the root directory:

```yaml
server:
  name: "Code Understanding Server"
  log_level: "info"
  host: "localhost"
  port: 8080

repositories:
  cache_dir: "./repo_cache"
  refresh_interval: 3600
  github:
    api_token: "${GITHUB_TOKEN}"

context:
  summary_depth: "medium"
  include_dependencies: true
  max_files_per_context: 100

parsers:
  enabled:
    - python
    - javascript
    - typescript
    - java
    - go
```

Set your GitHub API token in the environment:

```bash
export GITHUB_TOKEN="your-token-here"
```

## Usage

Start the server:

```bash
uv venv run python -m code_understanding.mcp.server.app
```

## MCP Tools

The server provides the following MCP tools:

- `get_context`: Generate structured context about a repository
- `get_resource`: Retrieve specific files or directory listings
- `answer_question`: Answer natural language questions about code
- `refresh_repo`: Update a remote repository with latest changes
- `clone_repo`: Clone a new remote repository

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