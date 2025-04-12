"""
RepoMap build management and background processing.
Following test_repo_map_simple.py's core RepoMap interaction patterns.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from aider.io import InputOutput
from aider.repomap import RepoMap

from .file_filter import FileFilter


class MinimalModel:
    """Minimal model implementation from test_repo_map_simple.py."""

    def token_count(self, text):
        # Rough approximation of token count
        return len(text.split()) * 1.3


class MinimalIO(InputOutput):
    """Minimal IO implementation from test_repo_map_simple.py."""

    def __init__(self):
        super().__init__()


class SubprocessManager:
    """Cross-platform subprocess handling."""

    async def run_command(self, cmd: List[str], **kwargs) -> str:
        """
        Execute command with proper encoding and error handling.
        Cross-platform compatible.
        """
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **kwargs,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Command failed: {stderr.decode()}")

        return stdout.decode()

    async def start_background_process(self, cmd: List[str]) -> asyncio.Task:
        """
        Start long-running process that is:
        - Non-blocking
        - Monitored
        - Properly cleaned up
        """

        async def _run_and_monitor():
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.wait()
            if proc.returncode != 0:
                raise RuntimeError(
                    f"Background process failed with code {proc.returncode}"
                )

        return asyncio.create_task(_run_and_monitor())


class RepoMapBuilder:
    """Manages RepoMap building process."""

    def __init__(self):
        # Track both the build task and its result
        self._building_repos: Dict[str, Tuple[asyncio.Task, Optional[str]]] = {}
        self._subprocess_manager = SubprocessManager()
        self.io = MinimalIO()
        self.model = MinimalModel()

    async def initialize_repo_map(
        self, root_dir: str, language: str = "python"
    ) -> RepoMap:
        """
        Initialize RepoMap following core patterns from test_repo_map_simple.py.

        Args:
            root_dir: Repository root directory
            language: Programming language for file filtering

        Returns:
            Initialized RepoMap instance
        """
        rm = RepoMap(
            root=root_dir,
            io=self.io,
            map_tokens=100000,  # As per example
            main_model=self.model,
            refresh="files",  # Critical setting
        )
        return rm

    async def gather_files(self, root_dir: str, language: str = "python") -> List[str]:
        """
        Gather files using the same filtering logic as test_repo_map_simple.py.

        Args:
            root_dir: Repository root directory
            language: Programming language for filtering

        Returns:
            List of files to include in RepoMap
        """
        file_filter = FileFilter.for_language(language)
        return file_filter.find_source_files(root_dir)

    async def start_build(self, repo_path: str, language: str = "python"):
        """
        Start RepoMap build process in the background.

        Args:
            repo_path: Path to repository
            language: Programming language for filtering
        """
        if repo_path in self._building_repos:
            # Build already in progress
            return

        async def _build():
            try:
                # Initialize RepoMap
                repo_map = await self.initialize_repo_map(repo_path, language)

                # Gather files
                files = await self.gather_files(repo_path, language)

                # Generate the map and store the output
                output = repo_map.get_ranked_tags_map([], files)

                # Store the result in our tracking dict
                self._building_repos[repo_path] = (
                    self._building_repos[repo_path][0],  # Keep the task
                    output,  # Store the result
                )

            except Exception as e:
                print(f"Error building RepoMap for {repo_path}: {e}")
                # Store None as the result to indicate failure
                self._building_repos[repo_path] = (
                    self._building_repos[repo_path][0],
                    None,
                )

        # Start build process and track it with no result yet
        task = asyncio.create_task(_build())
        self._building_repos[repo_path] = (task, None)

    async def is_building(self, repo_path: str) -> bool:
        """
        Check if RepoMap build is in progress.

        Args:
            repo_path: Repository path to check

        Returns:
            True if build is in progress, False otherwise
        """
        if repo_path not in self._building_repos:
            return False

        task, _ = self._building_repos[repo_path]
        return not task.done()

    async def get_build_result(self, repo_path: str) -> Optional[str]:
        """
        Get the RepoMap build result if available.

        Args:
            repo_path: Repository path to check

        Returns:
            The RepoMap output if build is complete, None if building or failed
        """
        if repo_path not in self._building_repos:
            return None

        task, result = self._building_repos[repo_path]
        if not task.done():
            return None

        return result

    def cleanup_build(self, repo_path: str):
        """
        Clean up build tracking for a repository.

        Args:
            repo_path: Repository path to clean up
        """
        if repo_path in self._building_repos:
            task, _ = self._building_repos[repo_path]
            if not task.done():
                task.cancel()
            del self._building_repos[repo_path]
