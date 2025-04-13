# MCP Code Understanding Service Implementation Specification

## Module Structure

```
src/
└── code_understanding/          # Root module directory
    ├── repository/             # Repository management
    │   ├── __init__.py
    │   ├── manager.py         # Core repo and git operations
    │   ├── path_utils.py      # Cross-platform path handling
    │   └── cache.py          # Repository caching implementation
    ├── context/               # RepoMap integration
    │   ├── __init__.py
    │   ├── builder.py        # RepoMap build management
    │   ├── file_filter.py    # PathSpec-based filtering
    │   └── extractor.py      # RepoMap output processing
    ├── pattern_search/        # Pattern search implementation
    │   ├── __init__.py
    │   └── searcher.py       # Pattern search using PathSpec
    └── mcp/
        └── server/
            └── app.py         # Thin API layer
```

## Detailed Component Specifications

### 1. Repository Management (`repository/`)

```python
# manager.py
class RepositoryManager:
    """Handles repository operations including git operations and RepoMap initialization."""

    async def clone_repository(self, url: str, branch: str = None) -> dict:
        """
        1. Clone repository
        2. Initialize RepoMap
        3. Start background build
        4. Return immediate response
        """

    async def refresh_repository(self, path: str) -> dict:
        """
        1. Pull latest changes
        2. Trigger RepoMap rebuild
        3. Return immediate response
        """

    async def _run_git_command(self, cmd: List[str], cwd: str) -> str:
        """
        Cross-platform git command execution
        Uses subprocess with proper encoding and error handling
        """

# cache.py
class RepositoryCache:
    """Manages repository caching and metadata."""

    async def get_cached_repo(self, url: str) -> Optional[str]:
        """
        Retrieve cached repository path if exists
        """

    async def cache_repo(self, url: str, path: str) -> None:
        """
        Cache repository metadata and path
        """

# path_utils.py
class PathUtils:
    """Cross-platform path handling utilities."""

    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalize path for current platform
        """

    @staticmethod
    def is_subpath(parent: str, child: str) -> bool:
        """
        Check if child path is subpath of parent
        """
```

### 2. RepoMap Integration (`context/`)

```python
# builder.py
class RepoMapBuilder:
    """Manages RepoMap building process."""

    def __init__(self):
        self._building_repos = {}  # Track ongoing builds
        self._subprocess_manager = SubprocessManager()

    async def start_build(self, repo_path: str):
        """
        1. Initialize RepoMap process
        2. Gather filtered files
        3. Start background build
        """

    async def is_building(self, repo_path: str) -> bool:
        """Check build status without exposing endpoint"""
```

### 3. File Filtering (`context/file_filter.py`)

```python
class FileFilter:
    """PathSpec-based file filtering."""

    def __init__(self, repo_path: str):
        self.gitignore_spec = self._load_gitignore()
        self.default_spec = self._create_default_spec()

    def get_included_files(self, root_dir: str) -> List[str]:
        """
        1. Scan directory
        2. Apply PathSpec filters
        3. Return included files
        """
```

### 4. Process Management

```python
class SubprocessManager:
    """Cross-platform subprocess handling."""

    async def run_command(self, cmd: List[str], **kwargs) -> str:
        """
        Execute command with:
        - Proper encoding
        - Error handling
        - Resource cleanup
        - Cross-platform compatibility
        """

    async def start_background_process(self, cmd: List[str]) -> asyncio.Task:
        """
        Start long-running process:
        - Non-blocking
        - Monitored
        - Properly cleaned up
        """
```

## API Endpoints

### 1. Clone Repository

```python
@mcp_server.tool(name="clone_repo")
async def clone_repo(url: str, branch: str = None) -> dict:
    """
    1. Clone repository
    2. Start RepoMap build
    3. Return immediately
    """
    return {
        "repo_path": str,
        "default_branch": str,
        "current_branch": str,
        "analysis_status": "pending"
    }
```

### 2. Get Context

```python
@mcp_server.tool(name="get_context")
async def get_context(
    repo_path: str,
    files: List[str] = None,
    directories: List[str] = None,
    max_tokens: int = None
) -> dict:
    """
    1. Check build status
    2. Return "building" message if needed
    3. Otherwise return context
    """
```

## Language Support

Initial language set with file patterns:

```python
LANGUAGE_PATTERNS = {
    "python": ["*.py"],
    "javascript": ["*.js", "*.jsx", "*.ts", "*.tsx"],
    "java": ["*.java"],
    "rust": ["*.rs"],
    "go": ["*.go"],
    "c": ["*.c", "*.h"],
    "cpp": ["*.cpp", "*.hpp"],
    "csharp": ["*.cs"],
    "ruby": ["*.rb"],
    "php": ["*.php"],
    "kotlin": ["*.kt"],
    "swift": ["*.swift"]
}
```

## Implementation Reference Guidelines

### RepoMap Integration Reference

```python
# Following test_repo_map_simple.py exactly:
class RepoMapBuilder:
    def __init__(self):
        self.io = MinimalIO()
        self.model = MinimalModel()

    async def initialize_repo_map(self, root_dir: str, language: str = "python"):
        """
        MUST follow test_repo_map_simple.py implementation:
        1. Initialize exactly as shown in example
        2. Use same configuration approach
        3. Follow same file gathering methodology
        """
        rm = RepoMap(
            root=root_dir,
            io=self.io,
            map_tokens=100000,  # As per example
            main_model=self.model,
            refresh="files",    # Critical setting
        )
        return rm

    async def gather_files(self, root_dir: str, language: str):
        """
        MUST use file gathering logic from test_repo_map_simple.py:
        1. Use same ignore patterns
        2. Follow same directory traversal
        3. Apply same filtering logic
        """
```

### Pattern Search Reference

```python
# Following pattern_search_test.py exactly:
class PatternSearcher:
    def __init__(self):
        self.exclude_patterns = DEFAULT_EXCLUDE_DIRS  # From example

    async def search_codebase(
        self,
        root_dir: str,
        search_pattern: str,
        file_pattern: Optional[str] = None,
        ignore_case: bool = False,
        max_results: Optional[int] = None,
    ) -> List[Dict]:
        """
        MUST implement as shown in pattern_search_test.py:
        1. Use same pattern matching logic
        2. Follow same file traversal method
        3. Implement same exclusion handling
        4. Use same result format
        """
```

### File Extraction Reference

```python
# Following extract_repo_files.py exactly:
class RepoMapExtractor:
    async def extract_files(self, repo_map_output: str) -> Set[str]:
        """
        MUST follow extract_repo_files.py implementation:
        1. Use same parsing logic
        2. Handle special characters identically
        3. Follow same file collection method
        """
        unique_files = set()
        # Implementation following example exactly
```

## Critical Implementation Notes

1. Example Script Adherence:

   - DO NOT deviate from example implementations
   - DO NOT "improve" or "optimize" the example code
   - DO NOT skip steps shown in examples
   - MUST follow error handling patterns shown
   - MUST use same configuration approaches

2. RepoMap Integration:

   - MUST follow `test_repo_map_simple.py` exactly
   - Any deviation requires explicit approval
   - Keep all configuration values as shown
   - Use same initialization pattern

3. Pattern Search:

   - MUST implement as shown in `pattern_search_test.py`
   - Keep all exclusion patterns
   - Follow same file traversal logic
   - Maintain same error handling

4. File Extraction:

   - MUST follow `extract_repo_files.py` patterns
   - Use same parsing methodology
   - Handle special characters identically
   - Maintain same output format

5. When Implementing:
   - Reference example scripts constantly
   - Verify against example implementations
   - Test against example outputs
   - Document any necessary deviations

## Testing Strategy

New test suite focusing on:

1. RepoMap integration
2. Background processing
3. File filtering
4. Cross-platform compatibility
5. API responses
6. Error handling

## Implementation Guidelines

1. Keep modules focused and independent
2. Use dependency injection
3. Handle all operations asynchronously
4. Provide clear error messages
5. Log important operations
6. Handle cross-platform differences
7. Follow existing coding patterns
