"""
Repository management and operations.
"""

import asyncio
from pathlib import Path
from typing import Dict, Optional, Any, Union
import time
import shutil
import logging

import git
from git.repo import Repo
import pathspec

from ..config import RepositoryConfig
from .path_utils import is_git_url, get_cache_path
from .cache import RepositoryCache

logger = logging.getLogger(__name__)


class Repository:
    def __init__(
        self,
        repo_id: str,
        root_path: Path,
        repo_type: str,
        is_git: bool,
        url: Optional[str] = None,
        branch: Optional[str] = None,
        manager: Optional["RepositoryManager"] = None,
    ):
        self.id = repo_id
        self.root_path = Path(root_path)
        self.repo_type = repo_type
        self.is_git = is_git
        self.url = url
        self.branch = branch
        self._git_repo: Optional[Repo] = None
        self._manager = manager

        if self.is_git and self.root_path.exists():
            self._git_repo = Repo(self.root_path)

    def is_ignored(self, path: Union[str, Path]) -> bool:
        """Check if a path should be ignored based on .gitignore patterns.

        Args:
            path: Path to check, either as string or Path object

        Returns:
            True if path matches any gitignore pattern, False otherwise
        """
        gitignore_path = self.root_path / ".gitignore"
        if not gitignore_path.exists():
            return False

        with open(gitignore_path, "r") as f:
            patterns = f.read().splitlines()

        spec = pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern, patterns
        )

        if isinstance(path, str):
            path = Path(path)

        rel_path = str(path.relative_to(self.root_path) if path.is_absolute() else path)
        return spec.match_file(rel_path)

    async def get_resource(self, resource_path: str) -> Dict[str, Any]:
        """Get contents of a file or directory listing."""
        if self._manager:
            await self._manager.cache.update_access(str(self.root_path))

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
        if self._manager:
            await self._manager.cache.update_access(str(self.root_path))

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
        self.repositories: Dict[str, Repository] = {}
        self.cache = RepositoryCache(self.cache_dir, config.max_cached_repos)

    def _cleanup_if_needed(self):
        """Remove least recently accessed repositories if over limit."""
        if len(self.repositories) <= self.config.max_cached_repos:
            return

        # Sort repositories by last access time
        sorted_repos = sorted(
            self.repositories.items(), key=lambda x: x[1].last_accessed
        )

        # Remove oldest repositories until under limit
        while len(self.repositories) > self.config.max_cached_repos:
            repo_id, repo = sorted_repos.pop(0)
            try:
                if repo.root_path.exists():
                    shutil.rmtree(repo.root_path)
                del self.repositories[repo_id]
            except Exception as e:
                print(f"Error removing repository {repo_id}: {e}")

    async def get_repository(self, path: str) -> Repository:
        """Get or create a Repository instance for the given path."""
        is_git = is_git_url(path)
        cache_path = get_cache_path(self.cache_dir, path)
        str_path = str(cache_path.resolve())  # Ensure absolute path

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

        # Update access time
        await self.cache.update_access(str(cache_path.resolve()))

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

        # Create or update repository instance
        repo_id = str(cache_path.resolve())  # Use absolute path as ID
        if repo_id in self.repositories:
            return self.repositories[repo_id]

        # Create new repository instance
        repository = Repository(
            repo_id=repo_id,
            root_path=cache_path.resolve(),  # Ensure absolute path
            repo_type="git" if is_git else "local",
            is_git=is_git_repo,
            url=path if is_git else url,
            manager=self,  # Pass manager reference
        )
        self.repositories[repo_id] = repository

        return repository

    async def clone_repository(
        self, url: str, branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clone a remote repository."""
        logger.info(f"Starting clone of repository: {url}")
        cache_path = get_cache_path(self.cache_dir, url)
        str_path = str(cache_path.resolve())  # Ensure absolute path
        logger.debug(f"Cache path for repository: {str_path}")

        # First, ensure we can add another repo
        logger.debug("Preparing cache for clone...")
        if not await self.cache.prepare_for_clone(str_path):
            logger.error("Failed to prepare cache for clone")
            return {"status": "error", "error": "Failed to prepare cache for clone"}

        try:
            # Create parent directories after prepare succeeds
            logger.debug(f"Creating parent directories: {cache_path.parent}")
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Perform the clone
            logger.info(f"Cloning repository from {url} to {cache_path}")
            git_repo = Repo.clone_from(url, cache_path, branch=branch)
            logger.info("Clone successful")

            # Register the new repo
            logger.debug("Registering repository in cache")
            await self.cache.add_repo(str_path, url)

            return {
                "status": "success",
                "path": str_path,
                "commit": str(git_repo.head.commit),
            }
        except Exception as e:
            logger.error(f"Error during clone: {str(e)}", exc_info=True)
            # Cleanup failed clone
            if cache_path.exists():
                logger.debug(f"Cleaning up failed clone at {cache_path}")
                shutil.rmtree(cache_path)
            return {"status": "error", "error": str(e)}

    async def refresh_repository(self, path: str) -> Dict[str, Any]:
        """Refresh a repository with latest changes."""
        try:
            repo = await self.get_repository(path)
            return await repo.refresh()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def cleanup(self):
        """Cleanup all repositories on server shutdown."""
        for repo_id, repo in list(self.repositories.items()):
            try:
                if repo.root_path.exists():
                    shutil.rmtree(repo.root_path)
                del self.repositories[repo_id]
            except Exception as e:
                print(f"Error cleaning up repository {repo_id}: {e}")
