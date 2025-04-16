"""
RepoMap build management and background processing.
Following test_repo_map_simple.py's core RepoMap interaction patterns.
"""

import asyncio
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from aider.io import InputOutput
from aider.repomap import RepoMap

from ..repository.cache import RepositoryCache, RepositoryMetadata
from .file_filter import FileFilter
from ..repository.path_utils import get_cache_path
from .extractor import RepoMapExtractor

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
        self, root_dir: str, max_tokens: Optional[int] = None
    ) -> RepoMap:
        """
        Initialize RepoMap following core patterns from test_repo_map_simple.py.

        Args:
            root_dir: Repository root directory
            max_tokens: Maximum tokens for repo map output. Defaults to 100000 if None.

        Returns:
            Initialized RepoMap instance
        """
        logger.debug(f"Initializing RepoMap for {root_dir} (max_tokens={max_tokens})")
        # TODO: It doesn't seem the blow mods are required, but keeping until I can confirm.
        # rm = RepoMap(
        #     root=root_dir,
        #     io=self.io,
        #     map_tokens=max_tokens if max_tokens is not None else 100000,
        #     map_mul_no_files=1,  # Prevent 8x multiplication
        #     max_context_window=None,  # Prevent context window expansion
        #     main_model=self.model,
        #     refresh="files",  # Critical setting
        # )

        # rm = RepoMap(
        #     root=root_dir,
        #     io=self.io,
        #     map_tokens=max_tokens if max_tokens is not None else 100000,
        #     main_model=self.model,
        #     refresh="files",  # Critical setting
        # )

        rm = RepoMap(
            root=root_dir,
            io=self.io,
            main_model=self.model,
            map_tokens=100000,  # Large token limit
            verbose=False,  # Changed from True to False to reduce output
        )
        return rm

    async def gather_files(self, root_dir: str) -> List[str]:
        """
        Gather all source files in the repository.

        Args:
            root_dir: Repository root directory

        Returns:
            List of files to include in RepoMap
        """
        file_filter = FileFilter()  # Create language-agnostic filter
        files = file_filter.find_source_files(root_dir)
        logger.debug(f"Found {len(files)} source files in {root_dir}")
        return files

    async def _do_build(self, repo_path: str):
        """
        Internal method to perform the actual build.
        """
        try:
            logger.debug(f"Starting RepoMap build for {repo_path}")
            repo_map = await self.initialize_repo_map(repo_path)
            files = await self.gather_files(repo_path)

            # Run CPU-intensive RepoMap generation in a thread pool
            output = await asyncio.to_thread(repo_map.get_ranked_tags_map, [], files)

            logger.debug(f"RepoMap generation complete for {repo_path}")

            # Update metadata with success status
            with self.cache._file_lock():
                metadata_dict = self.cache._read_metadata()
                if repo_path not in metadata_dict:
                    raise ValueError(f"Repository {repo_path} not found in cache")

                metadata = metadata_dict[repo_path]
                status = {"status": "complete", "completed_at": time.time()}
                metadata.repo_map_status = status
                self.cache._write_metadata(metadata_dict)

        except Exception as e:
            logger.error(f"Build failed for {repo_path}: {str(e)}")
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

    async def get_repo_map_content(
        self,
        repo_path: str,
        files: Optional[List[str]] = None,
        directories: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get repository map content if build is complete.
        Returns appropriate status/error messages otherwise.
        """
        cache_path = str(get_cache_path(self.cache.cache_dir, repo_path).resolve())
        logger.debug(
            f"Getting repo map content for {repo_path} (max_tokens={max_tokens})"
        )

        # Check status first without content generation
        with self.cache._file_lock():
            metadata_dict = self.cache._read_metadata()
            if cache_path not in metadata_dict:
                return {"status": "error", "error": "Repository not found in cache"}

            metadata = metadata_dict[cache_path]

            # Check clone status first
            clone_status = metadata.clone_status
            if not clone_status or clone_status["status"] != "complete":
                return {
                    "status": "waiting",
                    "message": f"Repository clone is {clone_status['status'] if clone_status else 'not_started'}",
                    "clone_status": clone_status
                    or {
                        "status": "not_started",
                        "started_at": None,
                        "completed_at": None,
                        "error": None,
                    },
                }

            # Then check repo map status
            if not metadata.repo_map_status:
                return {
                    "status": "error",
                    "error": "Repository map build has not been started",
                }

            if metadata.repo_map_status["status"] == "building":
                return {
                    "status": "building",
                    "message": "Repository map is still being built",
                    "estimated_completion_at": metadata.repo_map_status.get(
                        "estimated_completion_at"
                    ),
                }
            elif metadata.repo_map_status["status"] != "complete":
                return {
                    "status": "error",
                    "error": f"Repository map build failed or unknown status: {metadata.repo_map_status['status']}",
                }

        # Only proceed with content generation if both clone and build are complete
        try:
            repo_map = await self.initialize_repo_map(cache_path, max_tokens)
            all_files = await self.gather_files(cache_path)
            target_files = []

            # Filter files based on input parameters
            if files:
                target_files.extend(
                    f
                    for f in all_files
                    if any(f.endswith(specified_file) for specified_file in files)
                )
            if directories:
                for directory in directories:
                    dir_path = os.path.join(cache_path, directory)
                    target_files.extend(f for f in all_files if f.startswith(dir_path))
            if not files and not directories:
                target_files = all_files

            target_files = list(dict.fromkeys(target_files))
            logger.debug(f"Processing {len(target_files)} files")

            # Calculate token counts
            total_input_tokens = 0
            file_token_counts = {}
            for file in target_files:
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        content = f.read()
                        tokens = self.model.token_count(content)
                        total_input_tokens += tokens
                        file_token_counts[file] = tokens
                except Exception as e:
                    logger.warning(f"Failed to read {file}: {e}")

            logger.debug(f"Total input tokens: {total_input_tokens}")

            # Generate map and process results
            content = repo_map.get_ranked_tags_map([], target_files)

            # Dump raw content to file for debugging
            with open("raw_repomap_output.txt", "w", encoding="utf-8") as f:
                f.write(content)

            output_tokens = self.model.token_count(content)
            logger.debug(f"Generated map size: {output_tokens} tokens")

            # Process excluded files
            extractor = RepoMapExtractor()
            included_files = await extractor.extract_files(content)
            relative_target_files = {
                str(Path(f).relative_to(cache_path)) for f in target_files
            }
            excluded_files = relative_target_files - included_files

            if excluded_files:
                excluded_tokens = sum(
                    file_token_counts.get(f, 0)
                    for f in target_files
                    if str(Path(f).relative_to(cache_path)) in excluded_files
                )
                logger.debug(
                    f"Excluded {len(excluded_files)} files ({excluded_tokens} tokens)"
                )

            # Group excluded files by directory
            excluded_by_dir = {}
            for rel_file in excluded_files:
                abs_file = os.path.join(cache_path, rel_file)
                dir_path = str(Path(abs_file).parent)
                excluded_by_dir[dir_path] = excluded_by_dir.get(dir_path, 0) + 1

            return {
                "status": "success",
                "content": content,
                "metadata": {
                    "excluded_files_by_dir": excluded_by_dir,
                    "is_complete": len(excluded_files) == 0,
                    "max_tokens": max_tokens,
                },
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to generate repository map: {str(e)}",
            }
