# RepoMap Build Cleanup Plan

## Overview

This document outlines the strategy for managing and cleaning up RepoMap builds, ensuring no orphaned or stale builds remain in the system.

## Metadata Structure

Extend the existing metadata.json structure to include build status:

```json
{
  "/path/to/repo": {
    "url": "repo_url",
    "last_access": timestamp,
    "repo_map_status": {
      "status": "building|complete|failed",
      "started_at": timestamp,
      "build_id": "uuid",
      "pid": process_id,
      "completed_at": timestamp,
      "error": "error message if failed",
      "output_path": "path to output if complete"
    }
  }
}
```

## Cleanup Strategies

### 1. Process-Based Cleanup

Handle process termination and crashes:

```python
class RepoMapBuilder:
    async def start_build(self, repo_path: str):
        build_id = str(uuid.uuid4())
        with self.cache._file_lock():  # Use existing lock mechanism
            metadata = self.cache._read_metadata()
            metadata[repo_path]["repo_map_status"] = {
                "status": "building",
                "started_at": time.time(),
                "build_id": build_id,
                "pid": os.getpid()
            }
            self.cache._write_metadata(metadata)

        # Register cleanup handler
        atexit.register(self._cleanup_build, repo_path, build_id)
```

### 2. Time-Based Cleanup

Handle stale builds that exceed timeout:

```python
class RepoMapBuilder:
    TIMEOUT_HOURS = 2  # Build timeout threshold

    def is_stale_build(self, status: dict) -> bool:
        if status.get("status") == "building":
            started_at = status.get("started_at", 0)
            hours_elapsed = (time.time() - started_at) / 3600
            return hours_elapsed > self.TIMEOUT_HOURS
        return False

    async def cleanup_stale_builds(self):
        with self.cache._file_lock():
            metadata = self.cache._read_metadata()
            for repo_path, repo_data in metadata.items():
                build_status = repo_data.get("repo_map_status", {})
                if self.is_stale_build(build_status):
                    build_status.update({
                        "status": "failed",
                        "error": "Build timeout exceeded",
                        "completed_at": time.time()
                    })
            self.cache._write_metadata(metadata)
```

## Implementation Phases

### Phase 1: Basic Build Status Tracking

1. Extend metadata schema
2. Integrate with existing cache locking
3. Add basic build status updates

### Phase 2: Process Cleanup

1. Implement build ID generation
2. Add process tracking
3. Implement atexit handlers

### Phase 3: Time-Based Cleanup

1. Add timeout checking
2. Implement stale build cleanup
3. Add periodic cleanup task

## Error States

Build status can be one of:

- `building`: Build in progress
- `complete`: Build finished successfully
- `failed`: Build failed with error

Error conditions include:

1. Process termination
2. Timeout exceeded
3. RepoMap errors
4. System crashes

## Testing Strategy

1. Test process termination handling
2. Test timeout detection
3. Test concurrent build handling
4. Test metadata consistency
