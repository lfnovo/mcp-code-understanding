"""
Repository caching functionality.
"""

from pathlib import Path
from typing import Dict, Optional, Any, Set
from dataclasses import dataclass
import time
import shutil
import os
import json
import logging
import fcntl
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class RepositoryMetadata:
    path: str
    url: Optional[str]
    last_access: float


class RepositoryCache:
    def __init__(
        self, cache_dir: Path, max_cached_repos: int = 50, cleanup_interval: int = 86400
    ):
        self.cache_dir = Path(cache_dir)
        self.max_cached_repos = max_cached_repos
        self.cleanup_interval = cleanup_interval
        self.metadata_file = self.cache_dir / "metadata.json"
        self.lock_file = self.cache_dir / "cache.lock"

        # Create cache directory and lock file if they don't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if not self.lock_file.exists():
            self.lock_file.touch()

    @contextmanager
    def _file_lock(self):
        """File-based lock to handle concurrent operations"""
        with open(self.lock_file, "r") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _get_actual_repos(self) -> Set[str]:
        """Get set of actual repository paths on disk"""
        repos = set()
        # Walk through the cache directory structure:
        # repo_cache/github/org/repo-hash
        for host_dir in self.cache_dir.iterdir():
            if not host_dir.is_dir() or host_dir.name in {".git", "__pycache__"}:
                continue
            for org_dir in host_dir.iterdir():
                if not org_dir.is_dir():
                    continue
                for repo_dir in org_dir.iterdir():
                    if repo_dir.is_dir():
                        repos.add(str(repo_dir.resolve()))
        return repos

    def _read_metadata(self) -> Dict[str, RepositoryMetadata]:
        """Read and validate metadata from disk"""
        metadata = {}
        if self.metadata_file.exists():
            try:
                data = json.loads(self.metadata_file.read_text())
                for path, info in data.items():
                    metadata[path] = RepositoryMetadata(
                        path=path,
                        url=info.get("url"),
                        last_access=info.get("last_access", 0),
                    )
            except Exception as e:
                logger.error(f"Error reading metadata, starting fresh: {e}")
        return metadata

    def _write_metadata(self, metadata: Dict[str, RepositoryMetadata]):
        """Atomic metadata write"""
        temp_file = self.metadata_file.with_suffix(".tmp")
        try:
            data = {
                path: {"url": meta.url, "last_access": meta.last_access}
                for path, meta in metadata.items()
            }
            temp_file.write_text(json.dumps(data, indent=2))
            temp_file.replace(self.metadata_file)
        except Exception as e:
            logger.error(f"Error writing metadata: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise

    def _sync_metadata(self) -> Dict[str, RepositoryMetadata]:
        """Synchronize metadata with disk state"""
        metadata = self._read_metadata()
        actual_repos = self._get_actual_repos()

        # Remove metadata for missing repos
        for path in list(metadata.keys()):
            if path not in actual_repos:
                del metadata[path]

        # Add missing repos to metadata
        for path in actual_repos:
            if path not in metadata:
                metadata[path] = RepositoryMetadata(
                    path=path, url=None, last_access=time.time()
                )

        self._write_metadata(metadata)
        return metadata

    async def prepare_for_clone(self, target_path: str) -> bool:
        """
        Prepare cache for a new repository clone.
        Returns True if clone can proceed, False if not.
        """
        with self._file_lock():
            metadata = self._sync_metadata()

            # If target already exists, treat as success
            if target_path in metadata:
                return True

            # If we're at limit, cleanup oldest
            if len(metadata) >= self.max_cached_repos:
                sorted_repos = sorted(metadata.items(), key=lambda x: x[1].last_access)

                # Remove oldest repo
                oldest_path, _ = sorted_repos[0]
                try:
                    repo_path = Path(oldest_path)
                    if repo_path.exists():
                        shutil.rmtree(repo_path)
                    del metadata[oldest_path]
                    self._write_metadata(metadata)
                except Exception as e:
                    logger.error(f"Failed to remove old repo {oldest_path}: {e}")
                    return False

            return True

    async def add_repo(self, path: str, url: Optional[str] = None):
        """Register a new repository after successful clone"""
        with self._file_lock():
            metadata = self._sync_metadata()
            metadata[path] = RepositoryMetadata(
                path=path, url=url, last_access=time.time()
            )
            self._write_metadata(metadata)

    async def update_access(self, path: str):
        """Update access time for a repository"""
        with self._file_lock():
            metadata = self._sync_metadata()
            if path in metadata:
                metadata[path].last_access = time.time()
                self._write_metadata(metadata)

    async def remove_repo(self, path: str):
        """Remove a repository from cache"""
        with self._file_lock():
            metadata = self._sync_metadata()
            if path in metadata:
                try:
                    repo_path = Path(path)
                    if repo_path.exists():
                        shutil.rmtree(repo_path)
                    del metadata[path]
                    self._write_metadata(metadata)
                except Exception as e:
                    logger.error(f"Failed to remove repo {path}: {e}")
                    raise

    async def cleanup_old_repos(self):
        """Remove old cached repositories if over limit."""
        with self._file_lock():
            metadata = self._sync_metadata()

            if len(metadata) <= self.max_cached_repos:
                return

            # Sort by last access time
            sorted_repos = sorted(metadata.items(), key=lambda x: x[1].last_access)

            # Remove oldest until under limit
            while len(metadata) > self.max_cached_repos:
                oldest_path, _ = sorted_repos.pop(0)
                try:
                    repo_path = Path(oldest_path)
                    if repo_path.exists():
                        shutil.rmtree(repo_path)
                    del metadata[oldest_path]
                except Exception as e:
                    logger.error(f"Error removing repository {oldest_path}: {e}")

            self._write_metadata(metadata)
