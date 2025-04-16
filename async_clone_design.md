# Asynchronous Clone and Build Design

## Overview

Design for making both repository cloning and RepoMap building fully asynchronous, with proper status tracking and immediate client response.

## Component Changes

### 1. RepositoryMetadata Class

```python
@dataclass
class RepositoryMetadata:
    path: str
    url: Optional[str]
    last_access: float
    clone_status: Dict[str, Any] = None  # New field for clone status
    repo_map_status: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.clone_status is None:
            self.clone_status = {
                "status": "not_started",
                "started_at": None,
                "completed_at": None,
                "error": None
            }
```

### 2. RepositoryManager Changes

```python
async def _do_clone(self, url: str, cache_path: str, branch: Optional[str] = None):
    """Internal method to perform the actual clone"""
    try:
        # Update status to cloning
        await self.cache.update_clone_status(cache_path, {
            "status": "cloning",
            "started_at": time.time()
        })

        # Perform clone
        git_repo = Repo.clone_from(url, cache_path, branch=branch)

        # Update success status
        await self.cache.update_clone_status(cache_path, {
            "status": "cloned",
            "completed_at": time.time()
        })

        # Start RepoMap build
        repo_map_builder = RepoMapBuilder(self.cache)
        await repo_map_builder.start_build(cache_path)

    except Exception as e:
        # Update failure status
        await self.cache.update_clone_status(cache_path, {
            "status": "failed",
            "error": str(e),
            "completed_at": time.time()
        })
        # Cleanup failed clone
        if Path(cache_path).exists():
            shutil.rmtree(cache_path)
        raise

async def clone_repository(self, url: str, branch: Optional[str] = None) -> Dict[str, Any]:
    """Start asynchronous clone process"""
    cache_path = get_cache_path(self.cache_dir, url)
    str_path = str(cache_path.resolve())

    # Prepare cache and metadata
    if not await self.cache.prepare_for_clone(str_path):
        return {"status": "error", "error": "Failed to prepare cache for clone"}

    # Initialize metadata with cloning status
    await self.cache.add_repo(str_path, url)

    # Start clone in background
    asyncio.create_task(self._do_clone(url, str_path, branch))

    return {
        "status": "accepted",
        "path": str_path,
        "message": "Clone operation started"
    }
```

### 3. RepositoryCache Additions

```python
async def update_clone_status(self, path: str, status: Dict[str, Any]):
    """Update clone status in metadata"""
    with self._file_lock():
        metadata = self._sync_metadata()
        if path not in metadata:
            raise ValueError(f"Repository {path} not found in cache")

        metadata[path].clone_status.update(status)
        self._write_metadata(metadata)

async def get_clone_status(self, path: str) -> Dict[str, Any]:
    """Get current clone status"""
    with self._file_lock():
        metadata = self._sync_metadata()
        if path not in metadata:
            raise ValueError(f"Repository {path} not found in cache")

        return metadata[path].clone_status
```

### 4. MCP Server Endpoint Changes

```python
@mcp_server.tool(name="clone_repo")
async def clone_repo(url: str, branch: str = None) -> dict:
    try:
        result = await repo_manager.clone_repository(url, branch)
        if result["status"] == "accepted":
            logger.info(f"Clone operation started for {url}")
        return result
    except Exception as e:
        logger.error(f"Error initiating clone: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

@mcp_server.tool(name="get_clone_status")
async def get_clone_status(repo_path: str) -> dict:
    try:
        return await repo_manager.cache.get_clone_status(repo_path)
    except Exception as e:
        logger.error(f"Error getting clone status: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
```

### 5. Error Handling in get_repository

```python
async def get_repository(self, path: str) -> Repository:
    cache_path = get_cache_path(self.cache_dir, path)
    str_path = str(cache_path.resolve())

    # Check clone status first
    try:
        clone_status = await self.cache.get_clone_status(str_path)
        if clone_status["status"] == "cloning":
            raise ValueError("Repository is still being cloned")
        if clone_status["status"] == "failed":
            raise ValueError(f"Clone failed: {clone_status.get('error', 'Unknown error')}")
    except ValueError:
        if not cache_path.exists():
            # Start new clone if doesn't exist
            result = await self.clone_repository(path)
            if result["status"] != "accepted":
                raise ValueError(result.get("error", "Unknown error during clone"))
            raise ValueError("Repository clone has been initiated")

    # Rest of existing get_repository logic...
```

## Key Benefits

1. Consistent async pattern throughout
2. Better error handling and status tracking
3. No timeout issues for large repos
4. Clear status progression
5. Proper cleanup on failures
6. Client can poll both clone and build status

## Considerations

1. Race conditions during concurrent clone attempts
2. Disk space management during failed clones
3. Need to handle interrupted clones on server restart
4. Client needs to implement polling logic for both clone and build status

## Implementation Order

1. Update RepositoryMetadata class
2. Add new RepositoryCache methods
3. Modify RepositoryManager clone handling
4. Add new MCP server endpoints
5. Update error handling in get_repository
6. Add client-side polling support
