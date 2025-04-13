"""
RepoMap build management and background processing.
Following test_repo_map_simple.py's core RepoMap interaction patterns.
"""

import asyncio
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from aider.io import InputOutput
from aider.repomap import RepoMap

from ..repository.cache import RepositoryCache, RepositoryMetadata
from .file_filter import FileFilter

logger = logging.getLogger(__name__)


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

    def __init__(self, cache: RepositoryCache):
        self.io = MinimalIO()
        self.model = MinimalModel()
        self.cache = cache

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
        logger.debug(f"Initializing RepoMap for {root_dir} with language {language}")
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
        logger.debug(f"Gathering files for {root_dir}")
        file_filter = FileFilter.for_language(language)
        files = file_filter.find_source_files(root_dir)
        logger.debug(f"Found {len(files)} files to process")
        return files

    async def _do_build(self, repo_path: str, language: str = "python"):
        """
        Internal method to perform the actual build.
        """
        try:
            # Initialize RepoMap
            logger.debug("Initializing RepoMap...")
            repo_map = await self.initialize_repo_map(repo_path, language)

            # Gather files
            logger.debug("Gathering files...")
            files = await self.gather_files(repo_path, language)

            # Generate the map
            logger.debug("Generating RepoMap...")
            output = repo_map.get_ranked_tags_map([], files)

            # Log preview of the output
            logger.debug("RepoMap generation complete. First 20 lines preview:")
            output_lines = output.split("\n")
            for i, line in enumerate(output_lines[:20]):
                logger.debug(f"Line {i+1}: {line}")
            if len(output_lines) > 20:
                logger.debug(f"... and {len(output_lines) - 20} more lines")

            # Update metadata with success status
            with self.cache._file_lock():
                metadata_dict = self.cache._read_metadata()
                if repo_path not in metadata_dict:
                    raise ValueError(f"Repository {repo_path} not found in cache")

                metadata = metadata_dict[repo_path]
                status = {
                    "status": "complete",
                    "completed_at": time.time(),
                    "output": output,  # Store the RepoMap output
                }
                metadata.repo_map_status = status

                # Write back the updated metadata
                self.cache._write_metadata(metadata_dict)

            logger.debug("Build completed successfully")

        except Exception as e:
            logger.error(f"Build failed: {str(e)}")
            # Update metadata with failure status
            with self.cache._file_lock():
                metadata_dict = self.cache._read_metadata()
                if repo_path not in metadata_dict:
                    raise ValueError(f"Repository {repo_path} not found in cache")

                metadata = metadata_dict[repo_path]
                status = {
                    "status": "failed",
                    "completed_at": time.time(),
                    "error": str(e),
                }
                metadata.repo_map_status = status

                # Write back the updated metadata
                self.cache._write_metadata(metadata_dict)
            raise

    async def start_build(self, repo_path: str) -> None:
        """Start building RepoMap for a repository."""
        logger.debug(f"Starting RepoMap build for {repo_path}")

        # Get repository metadata
        with self.cache._file_lock():
            metadata_dict = self.cache._read_metadata()
            if repo_path not in metadata_dict:
                raise ValueError(f"Repository {repo_path} not found in cache")

            metadata = metadata_dict[repo_path]

            # Calculate rough estimate of completion time
            # TODO: Implement more sophisticated estimation based on codebase size/complexity
            total_size = 0
            for root, _, files in os.walk(repo_path):
                for file in files:
                    try:
                        total_size += os.path.getsize(os.path.join(root, file))
                    except (OSError, IOError):
                        continue

            # Very rough estimate: 1 second per 100KB of code
            estimated_seconds = max(1, total_size / (100 * 1024))
            estimated_completion = time.time() + estimated_seconds

            # Update build status
            metadata.repo_map_status = {
                "status": "building",
                "estimated_completion_at": estimated_completion,
                "message": "Building repository map for AI analysis",
            }
            self.cache._write_metadata(metadata_dict)

        # Start build process in background
        asyncio.create_task(self._do_build(repo_path))

    async def get_build_status(self, repo_path: str) -> dict:
        """Get current build status for a repository."""
        with self.cache._file_lock():
            metadata_dict = self.cache._read_metadata()
            if repo_path not in metadata_dict:
                raise ValueError(f"Repository {repo_path} not found in cache")

            metadata = metadata_dict[repo_path]
            if not metadata.repo_map_status:
                return {"status": "not_started"}

            return metadata.repo_map_status
