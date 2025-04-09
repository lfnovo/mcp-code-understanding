"""
Repository caching functionality.
"""

from pathlib import Path
from typing import Dict, Optional, Any
import time
import shutil
import os
import json
import logging

logger = logging.getLogger(__name__)


class RepositoryMetadata:
    def __init__(self, repo_path: str, initial_clone_time: float = None):
        self.repo_path = repo_path
        self.initial_clone_time = initial_clone_time or time.time()
        self.last_refresh_time = self.initial_clone_time

    def to_dict(self) -> dict:
        return {
            "repo_path": self.repo_path,
            "initial_clone_time": self.initial_clone_time,
            "last_refresh_time": self.last_refresh_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RepositoryMetadata":
        metadata = cls(data["repo_path"], data["initial_clone_time"])
        metadata.last_refresh_time = data["last_refresh_time"]
        return metadata


class RepositoryCache:
    def __init__(
        self, cache_dir: Path, max_cached_repos: int = 50, cleanup_interval: int = 86400
    ):
        self.cache_dir = Path(cache_dir)
        self.max_cached_repos = max_cached_repos
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.repo_metadata: Dict[str, RepositoryMetadata] = {}

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_metadata()

    def _load_metadata(self):
        """Load repository metadata from disk."""
        if self.metadata_file.exists():
            try:
                data = json.loads(self.metadata_file.read_text())
                self.repo_metadata = {
                    path: RepositoryMetadata.from_dict(meta)
                    for path, meta in data.items()
                }
            except Exception as e:
                logger.error(f"Error loading cache metadata: {e}")
                self.repo_metadata = {}

    def _save_metadata(self):
        """Save repository metadata to disk."""
        try:
            data = {path: meta.to_dict() for path, meta in self.repo_metadata.items()}
            self.metadata_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Error saving cache metadata: {e}")

    def update_repo_timestamp(self, repo_path: str, is_new: bool = False):
        """Update repository timestamp on clone or refresh."""
        if is_new:
            metadata = RepositoryMetadata(repo_path)
            self.repo_metadata[repo_path] = metadata
        else:
            if repo_path in self.repo_metadata:
                self.repo_metadata[repo_path].last_refresh_time = time.time()
        self._save_metadata()

    async def cleanup_old_repos(self):
        """Remove old cached repositories if over limit."""
        current_time = time.time()

        # Only run cleanup if enough time has passed
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        # Verify all metadata entries still exist
        for repo_path in list(self.repo_metadata.keys()):
            if not Path(repo_path).exists():
                del self.repo_metadata[repo_path]

        # If under limit, no cleanup needed
        if len(self.repo_metadata) <= self.max_cached_repos:
            self.last_cleanup = current_time
            self._save_metadata()
            return

        # Sort by last refresh time (oldest first)
        sorted_repos = sorted(
            self.repo_metadata.items(), key=lambda x: x[1].last_refresh_time
        )

        # Remove oldest repositories until under limit
        num_to_remove = len(sorted_repos) - self.max_cached_repos
        for repo_path, _ in sorted_repos[:num_to_remove]:
            try:
                repo_dir = Path(repo_path)
                if repo_dir.exists():
                    shutil.rmtree(repo_dir)
                del self.repo_metadata[repo_path]
                logger.info(f"Removed old repository: {repo_path}")
            except Exception as e:
                logger.error(f"Error removing repository {repo_path}: {e}")

        self.last_cleanup = current_time
        self._save_metadata()
