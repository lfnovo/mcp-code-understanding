"""
Repository management and operations.
"""
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
import uuid

import git
from git.repo import Repo

from .config import RepositoryConfig

class Repository:
    def __init__(self, repo_id: str, root_path: Path, repo_type: str, 
                 is_git: bool, url: Optional[str] = None, branch: Optional[str] = None):
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
                "content": path.read_text()
            }
        else:
            return {
                "type": "directory",
                "path": str(resource_path),
                "contents": [
                    str(p.relative_to(self.root_path)) 
                    for p in path.iterdir()
                ]
            }
    
    async def refresh(self) -> Dict[str, Any]:
        """Update repository with latest changes."""
        if not self.is_git or not self._git_repo:
            return {"status": "not_git_repo"}
        
        try:
            origin = self._git_repo.remotes.origin
            origin.pull()
            return {
                "status": "success",
                "commit": str(self._git_repo.head.commit)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

class RepositoryManager:
    def __init__(self, config: RepositoryConfig):
        self.config = config
        self.cache_dir = Path(config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.repositories: Dict[str, Repository] = {}
    
    async def get_repository(self, path: str) -> Repository:
        """Get or create a Repository instance for the given path."""
        path = Path(path).resolve()
        
        if str(path) in self.repositories:
            return self.repositories[str(path)]
        
        # Check if it's a Git repository
        is_git = False
        url = None
        try:
            repo = Repo(path)
            is_git = True
            if len(repo.remotes) > 0:
                url = repo.remotes.origin.url
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            pass
        
        repo = Repository(
            repo_id=str(uuid.uuid4()),
            root_path=path,
            repo_type="local" if not is_git else "git",
            is_git=is_git,
            url=url
        )
        
        self.repositories[str(path)] = repo
        return repo
    
    async def clone_repository(self, url: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """Clone a remote repository."""
        repo_dir = self.cache_dir / str(uuid.uuid4())
        
        try:
            git_repo = Repo.clone_from(url, repo_dir, branch=branch)
            repo = Repository(
                repo_id=str(uuid.uuid4()),
                root_path=repo_dir,
                repo_type="git",
                is_git=True,
                url=url,
                branch=branch
            )
            self.repositories[str(repo_dir)] = repo
            
            return {
                "status": "success",
                "path": str(repo_dir),
                "commit": str(git_repo.head.commit)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def refresh_repository(self, path: str) -> Dict[str, Any]:
        """Refresh a repository with latest changes."""
        try:
            repo = await self.get_repository(path)
            return await repo.refresh()
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def cleanup(self):
        """Cleanup temporary repositories."""
        # Implement cleanup logic for cached repositories
