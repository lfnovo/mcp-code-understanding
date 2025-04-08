"""
Repository management and operations.
"""

import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
import uuid

import git
from git.repo import Repo

from ..config import RepositoryConfig
from .path_utils import is_git_url, get_cache_path


class Repository:
    def __init__(
        self,
        repo_id: str,
        root_path: Path,
        repo_type: str,
        is_git: bool,
        url: Optional[str] = None,
        branch: Optional[str] = None,
    ):
        self.id = repo_id
        self.root_path = Path(root_path)
        self.repo_type = repo_type
        self.is_git = is_git
        self.url = url
        self.branch = branch
        self._git_repo: Optional[Repo] = None

        if self.is_git and self.root_path.exists():
            self._git_repo = Repo(self.root_path)

    async def get_resource(self, resource_path: str) -> Dict[str, Any]:
        """Get contents of a file or directory listing."""
        path = self.root_path / resource_path

        if not path.exists():
            raise FileNotFoundError(f"Resource not found: {resource_path}")

        if path.is_file():
            return {
                "type": "file",
                "path": str(resource_path),
                "content": path.read_text(),
            }
        else:
            return {
                "type": "directory",
                "path": str(resource_path),
                "contents": [
                    str(p.relative_to(self.root_path)) for p in path.iterdir()
                ],
            }

    async def refresh(self) -> Dict[str, Any]:
        """Update repository with latest changes."""
        if not self.is_git or not self._git_repo:
            return {"status": "not_git_repo"}

        try:
            origin = self._git_repo.remotes.origin
            origin.pull()
            return {"status": "success", "commit": str(self._git_repo.head.commit)}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class RepositoryManager:
    def __init__(self, config: RepositoryConfig):
        self.config = config
        self.cache_dir = Path(config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def get_repository(self, path: str) -> Repository:
        """Get or create a Repository instance for the given path."""
        is_git = is_git_url(path)
        cache_path = get_cache_path(self.cache_dir, path)

        # If it's a Git URL and not cached, clone it
        if is_git and not cache_path.exists():
            try:
                result = await self.clone_repository(path)
                if result["status"] != "success":
                    raise Exception(result.get("error", "Unknown error during clone"))
                cache_path = Path(result["path"])
            except Exception as e:
                raise Exception(f"Failed to clone repository: {e}")

        # For local paths that aren't in cache, verify they exist
        if not is_git and not cache_path.exists():
            original_path = Path(path).resolve()
            if not original_path.exists():
                raise FileNotFoundError(f"Repository not found: {path}")
            # Local repository exists but isn't cached
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            # For now, just use the original path
            cache_path = original_path

        # Check if it's a Git repository
        is_git_repo = False
        url = None
        try:
            repo = Repo(cache_path)
            is_git_repo = True
            if len(repo.remotes) > 0:
                url = repo.remotes.origin.url
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            pass

        return Repository(
            repo_id=cache_path.name,
            root_path=cache_path,
            repo_type="git" if is_git else "local",
            is_git=is_git_repo,
            url=path if is_git else url,
        )

    async def clone_repository(
        self, url: str, branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clone a remote repository."""
        cache_path = get_cache_path(self.cache_dir, url)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            git_repo = Repo.clone_from(url, cache_path, branch=branch)
            return {
                "status": "success",
                "path": str(cache_path),
                "commit": str(git_repo.head.commit),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def refresh_repository(self, path: str) -> Dict[str, Any]:
        """Refresh a repository with latest changes."""
        try:
            repo = await self.get_repository(path)
            return await repo.refresh()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def cleanup(self):
        """Cleanup temporary repositories."""
        # TODO: Implement cleanup based on access time
        pass
