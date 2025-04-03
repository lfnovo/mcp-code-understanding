# Code Understanding MCP Server

An MCP (Model Context Protocol) server designed to understand codebases and provide intelligent context to AI coding assistants. This server handles both local and remote GitHub repositories and supports standard MCP-compliant operations.

## Features

- MCP-compliant server implementation using FastMCP
- Local and remote Git repository support
- Code parsing and analysis
- Natural language Q&A about codebases
- Extensible parser architecture

## Installation

1. Ensure you have Python 3.11+ installed
2. Clone this repository
3. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

4. Install dependencies:

```bash
pip install -e .
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
python -m code_understanding.mcp.server.app
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
pytest
```

Format code:

```bash
black .
isort .
```

Type checking:

```bash
mypy .
```

## License

MIT
