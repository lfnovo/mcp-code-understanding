# MCP API Specification

## Core Repository Operations

### Clone Repository

```python
async def clone_repo(
    url: str,
    branch: str = None
) -> dict:
"""
Clones a repository and initiates background RepoMap analysis.
Returns immediately with repo info while analysis continues.

Returns:
{
    "repo_path": str,        # Path to use in other API calls
    "default_branch": str,   # The default/main branch
    "current_branch": str,   # Currently checked out branch
    "analysis_status": str   # "pending" while RepoMap processes
}
"""
```

### Refresh Repository

```python
async def refresh_repo(
    repo_path: str
) -> dict:
"""
Updates repository to latest and triggers new RepoMap analysis.
Returns immediately while analysis runs in background.

Returns:
{
    "current_branch": str,   # Currently checked out branch
    "analysis_status": str   # "pending" while RepoMap processes
}
"""
```

## Code Analysis and Search

### Get Context

```python
async def get_context(
    repo_path: str,
    files: List[str] = None,
    directories: List[str] = None,
    max_tokens: int = None
) -> dict:
"""
Returns RepoMap's semantic analysis of specified files/directories.
- If files/directories are None: analyzes all source files
- Directories are expanded to their contained files
- Uses RepoMap's caching for efficiency
- see "extract_repo_files.py" for an example of how we plan to parse the repo map that's returned by Ader in order to do a comparison of the files in the codebase versus the files returned by Ader's repo map. The idea would be to call repo map, extract the files using this method, do a comparison between the complete list of files in the repo, and then include any files that were in the repo, but not in ADERS repo map in the excluded files by dir response.

Returns:
{
    "content": str,          # The RepoMap output
    "metadata": {
        "excluded_files_by_dir": {      # Files omitted due to token limit
            "path/to/dir/": int,        # Count of files excluded in dir
            ...
        },
        "is_complete": bool,            # Whether all files were included
        "max_tokens": int               # Token limit used for RepoMap
    }
}
"""
```

### Get Resource

```python
async def get_resource(
    repo_path: str,
    resource_path: str
) -> dict:
"""
Returns raw contents and metadata for a specific file.
Useful for getting complete file contents after RepoMap analysis.

Returns:
{
    "content": str          # Raw file contents
}
"""
```

### Pattern Search

```python
async def pattern_search(
    root_dir: str,
    search_pattern: str,
    file_pattern: str = None,
    ignore_case: bool = False,
    max_results: int = None
) -> dict:
"""
Performs pattern-based code search using a pure Python implementation.
This endpoint's implementation has been validated with a dedicated test script
that was developed and tested.

Parameters:
- root_dir: Root directory to search in
- search_pattern: Regular expression pattern to search for
- file_pattern: Optional glob pattern to filter files (e.g. "*.py")
- ignore_case: Whether to perform case-insensitive matching
- max_results: Optional limit on number of results
- see the "pattern_search_test.py" Script for an example of how we need to implement pattern searches. Follow this method and only implement code after thoroughly understanding it. If you have questions or need clarification, you will not write or update the code, but you will stop and ask for clarification. I've thoroughly tested and validated the results of this script and it works as I intend.

Returns:
{
    "matches": [
        {
            "file": str,     # File path relative to root_dir
            "line": int,     # Line number
            "content": str   # The matching line content
        },
        ...
    ],
    "total_matches": int    # Total number of matches found
}

Notes:
- Implementation uses os.walk() and re module for portability
- Handles binary files and permission errors gracefully
- Uses default exclusions listed below
- A standalone test script exists demonstrating this exact implementation
"""
```

## Default Exclusions

Apply all appropriate exclusion patterns during searches. Examples:

### Python

- `venv/`
- `env/`
- `.env/`
- `.venv/`
- `__pycache__/`
- `*.pyc`
- `.pytest_cache/`
- `.coverage`
- `htmlcov/`
- `dist/`
- `build/`
- `*.egg-info/`
- `.tox/`

### Java

- `target/`
- `build/`
- `.gradle/`
- `out/`
- `bin/`
- `.settings/`
- `.idea/`
- `*.class`
- `*.jar`
- `*.war`

### Version Control

- `.git/`
- `.svn/`
- `.hg/`

### IDE and Editor Files

- `.vscode/`
- `.idea/`
- `*.swp`
- `*.swo`
- `.DS_Store`
- `Thumbs.db`

### Interfacing with Ader's repo map class

See the "test_repo_map_simple.py" Script for an example of how we need to interface with Ader's repo map class to have it build and return repo maps for files in our code base. When planning or implementing this, be sure to either strictly adhere to this or, if deviating, stop and ask for clarification or guidance before modifying any code related to this. This method has been thoroughly tested and validated and known to work.

### Important constraints and considerations

1. During clone repo or refresh repo operations, we gather up and pass all relevant files from a repo, meaning those that are not either in the .getignore repo list and also not in our own default exclusion list, and pass them to repo map to start Ader building the repo map.
2. Because building a complete repo map can take time, it's imperative that we perform this in the background and immediately return to the client. It's also critical that whatever background processing Python methods that we choose to use are completely OS-compatible, Windows, Mac OS, and Linux, and that we make sure we don't use any particular methods that won't work on, say, newer versions of Windows or with newer versions of Python. Such as 3.12 unless we restrict our dependencies because I know there are issues with 3.12 with certain Python background processing methods.
3. Although not explicitly listed in the endpoint APIs above, we will need some method to notify the client when it requests any operations that leverage the repo map, that the repo map has not been completely created at that point. In fact, I think it's probably best that we just return some message, in this case, to the client to say, RepoMap still building. Check back in a couple seconds, something to that effect.
