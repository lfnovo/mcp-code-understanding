"""
RepoMap build management and background processing.
Following test_repo_map_simple.py's core RepoMap interaction patterns.
"""

import asyncio
import os
import time
import logging
import tiktoken
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from aider.io import InputOutput
from aider.repomap import RepoMap
from .extended_repo_map import UntruncatedRepoMap

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


class TiktokenModel:
    """Model implementation using tiktoken for exact GPT-2 token counts."""

    def __init__(self):
        # Initialize the GPT-2 encoder
        self.encoder = tiktoken.get_encoding("gpt2")

    def token_count(self, text):
        """
        Get exact token count using GPT-2 tokenizer.

        Args:
            text: Text to count tokens for

        Returns:
            Exact token count
        """
        return len(self.encoder.encode(text))


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
        # self.model = MinimalModel()
        self.model = TiktokenModel()
        self.cache = cache

    async def initialize_repo_map(
        self, root_dir: str, max_tokens: Optional[int] = None
    ) -> RepoMap:
        """
        Initialize RepoMap following core patterns from test_repo_map_simple.py.

        Args:
            root_dir: Repository root directory
            max_tokens: Maximum tokens for repo map output. Defaults to 1000000 if None.

        Returns:
            Initialized UntruncatedRepoMap instance
        """
        logger.debug(f"Initializing RepoMap for {root_dir} (max_tokens={max_tokens})")
        rm = UntruncatedRepoMap(
            root=root_dir,
            io=self.io,
            main_model=self.model,
            map_tokens=max_tokens if max_tokens is not None else 1000000,
            refresh="files",
            max_context_window=max_tokens if max_tokens is not None else 1000000,
        )
        return rm

    async def gather_files(self, root_dir: str) -> List[str]:
        """
        Gather all source files in the repository that match our extension and text criteria.

        Args:
            root_dir: Repository root directory

        Returns:
            List of files to include in RepoMap
        """
        file_filter = FileFilter()  # Create filter with extension-based inclusion
        files = file_filter.find_source_files(root_dir)
        logger.debug(
            f"Found {len(files)} files matching extension and text criteria in {root_dir}"
        )
        return files

    async def gather_files_targeted(
        self,
        root_dir: str,
        files: Optional[List[str]] = None,
        directories: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Optimized file gathering that only checks specified directories or files.
        Files must match our extension and text criteria to be included.

        Args:
            root_dir: Repository root directory
            files: Optional list of specific files to check
            directories: Optional list of directories to scan

        Returns:
            List of valid source files that match the criteria
        """
        file_filter = FileFilter()
        target_files = []

        if files:
            # Direct file checking
            for file in files:
                file_path = os.path.join(root_dir, file)
                if os.path.exists(file_path) and file_filter.should_include(file_path):
                    target_files.append(file_path)

        if directories:
            # Scan specified directories using our extension and text filtering
            for directory in directories:
                dir_path = os.path.join(root_dir, directory)
                if os.path.exists(dir_path) and os.path.isdir(dir_path):
                    target_files.extend(file_filter.find_source_files(dir_path))

        target_files = list(dict.fromkeys(target_files))  # Remove duplicates
        logger.debug(
            f"Found {len(target_files)} source files in specified paths within {root_dir}"
        )
        return sorted(target_files)

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

    async def filter_files_by_token_limit(
        self, files: List[str], max_tokens: Optional[int]
    ) -> Tuple[List[str], Dict[str, int]]:
        """
        Filter files to stay within token limit.

        Args:
            files: List of file paths to filter
            max_tokens: Maximum total tokens allowed, or None for no limit

        Returns:
            Tuple of (filtered file list, dict of file token counts)
        """
        if not max_tokens:
            return files, {}

        # Sort files by size as initial proxy for token count
        files_by_size = sorted(files, key=lambda f: os.path.getsize(f))

        filtered_files = []
        file_token_counts = {}
        total_tokens = 0

        for file in files_by_size:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                    tokens = self.model.token_count(content)

                    # Skip files that would exceed the limit
                    if total_tokens + tokens > max_tokens:
                        continue

                    total_tokens += tokens
                    file_token_counts[file] = tokens
                    filtered_files.append(file)
            except Exception as e:
                logger.warning(f"Failed to read {file}: {e}")

        logger.debug(
            f"Filtered {len(files)} files to {len(filtered_files)} within {max_tokens} token limit"
        )
        return filtered_files, file_token_counts

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

            # Use optimized gathering if specific files/directories are provided
            if files or directories:
                target_files = await self.gather_files_targeted(
                    cache_path, files=files, directories=directories
                )
            else:
                # Fall back to full repository scan if no specific paths provided
                all_files = await self.gather_files(cache_path)
                target_files = all_files

            logger.debug(f"Processing {len(target_files)} files")

            # Save complete list before filtering
            all_target_files = target_files.copy()

            # Pre-filter files based on token limit
            # target_files, file_token_counts = await self.filter_files_by_token_limit(
            #     target_files, max_tokens
            # )

            # logger.debug(f"Filtered to {len(target_files)} files within token limit")
            # Calculate total tokens for logging
            # total_input_tokens = sum(file_token_counts.values())
            # logger.debug(f"Total input tokens: {total_input_tokens}")

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
            normalized_included_files = {os.path.normpath(f) for f in included_files}

            # Convert and normalize ALL original files for comparison
            all_relative_target_files = {
                os.path.normpath(str(Path(f).relative_to(cache_path)))
                for f in all_target_files
            }

            # Compare against ALL files, not just filtered ones
            excluded_files = all_relative_target_files - normalized_included_files

            if excluded_files:
                # excluded_tokens = sum(
                #     file_token_counts.get(f, 0)
                #     for f in target_files
                #     if os.path.normpath(str(Path(f).relative_to(cache_path)))
                #     in excluded_files
                # )
                # logger.debug(
                #     f"Excluded {len(excluded_files)} files ({excluded_tokens} tokens)"
                # )
                logger.debug(f"Excluded {len(excluded_files)} files")

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
                    "output_tokens": output_tokens,
                },
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to generate repository map: {str(e)}",
            }
