"""
RepoMap build management and background processing.
Following test_repo_map_simple.py's core RepoMap interaction patterns.
"""

import asyncio
import os
import time
from datetime import datetime
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
    """Minimal IO implementation that prevents any stdout writes."""

    def __init__(self):
        super().__init__(pretty=False)

    def tool_output(self, text, **kwargs):
        """Override to prevent tool output to stdout"""
        pass

    def tool_error(self, text, **kwargs):
        """Override to prevent error output to stdout"""
        pass

    def prompt_for_input(self, prompt, **kwargs):
        """Override to prevent input prompts"""
        pass

    def prompt_for_yesno(self, prompt, default=None, **kwargs):
        """Override to prevent yes/no prompts"""
        return True

    def get_input(self, **kwargs):
        """Override to prevent input requests"""
        return ""

    def show_tool_output_command(self, command, output, returncode, **kwargs):
        """Override to prevent command output display"""
        pass

    def show_tool_error(self, command, output, returncode, **kwargs):
        """Override to prevent error display"""
        pass

    def info_message(self, msg, **kwargs):
        """Override to prevent info messages"""
        pass

    def warning_message(self, msg, **kwargs):
        """Override to prevent warning messages"""
        pass

    def error_message(self, msg, **kwargs):
        """Override to prevent error messages"""
        pass


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

    def _get_retry_guidance(self, file_count: int) -> Dict[str, Any]:
        """
        Get retry guidance based on file count.

        Args:
            file_count: Number of matching files

        Returns:
            Dictionary containing retry guidance with suggested wait time and context
        """
        if file_count < 100:
            category = "tiny"
            seconds = 5
        elif file_count < 1000:
            category = "small"
            seconds = 15
        elif file_count < 10000:
            category = "medium"
            seconds = 30
        else:
            category = "large"
            seconds = 60

        return {
            "suggested_retry_seconds": seconds,
            "size_context": f"{category.capitalize()} repository ({file_count} matching files), initial build in progress",
        }

    async def initialize_repo_map(
        self,
        root_dir: str,
        max_tokens: Optional[int] = None,
        is_full_build: bool = False,  # New parameter to indicate if this is a full build
    ) -> RepoMap:
        """
        Initialize RepoMap following core patterns from test_repo_map_simple.py.

        Args:
            root_dir: Repository root directory
            max_tokens: Maximum tokens for repo map output. Defaults to 1000000 if None.
            is_full_build: Whether this is a full build operation (initial or post-refresh)

        Returns:
            Initialized UntruncatedRepoMap instance
        """
        logger.debug(
            f"Initializing RepoMap for {root_dir} (max_tokens={max_tokens}, refresh={'always' if is_full_build else 'files'})"
        )
        rm = UntruncatedRepoMap(
            root=root_dir,
            io=self.io,
            main_model=self.model,
            map_tokens=max_tokens if max_tokens is not None else 1000000,
            refresh=(
                "always" if is_full_build else "files"
            ),  # Set based on operation type
            max_context_window=max_tokens if max_tokens is not None else 1000000,
        )
        return rm

    async def gather_files(self, root_dir: str) -> List[str]:
        """
        Gather all source files in the repository that match our extension and text criteria.
        Always performs a fresh scan of the directory.

        Args:
            root_dir: Repository root directory

        Returns:
            List of files to include in RepoMap
        """
        file_filter = FileFilter()  # Create new filter instance each time
        files = file_filter.find_source_files(root_dir)  # This does a fresh scan
        logger.debug(
            f"Found {len(files)} files matching extension and text criteria in {root_dir}"
        )
        return sorted(files)  # Sort for consistent ordering

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
            repo_map = await self.initialize_repo_map(
                repo_path, is_full_build=True
            )  # This is a full build
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
                status = {
                    "status": "complete",
                    "completed_at": datetime.now().isoformat(),
                }
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
                    "completed_at": datetime.now().isoformat(),
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

            # Get matching files count for retry guidance
            matching_files = len(await self.gather_files(repo_path))

            # Update build status
            metadata.repo_map_status = {
                "status": "building",
                "matching_files": matching_files,
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
        files: List[str] = None,
        directories: List[str] = None,
        max_tokens: int = None,
        max_files_threshold: int = None,
    ) -> Dict[str, Any]:
        """
        Get repository map content if build is complete.
        Returns appropriate status/error messages otherwise.
        Token limiting is handled by Aider's RepoMap based on max_tokens parameter.
        Files exceeding max_files_threshold will return early with guidance.
        """
        DEFAULT_FILES_THRESHOLD = 5000

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
                    "retry_guidance": {
                        "suggested_retry_seconds": 30,  # Conservative default during clone
                        "size_context": "Repository clone in progress, size unknown",
                    },
                }

            # Then check repo map status
            if not metadata.repo_map_status:
                return {
                    "status": "error",
                    "error": "Repository map build has not been started",
                }

            if metadata.repo_map_status["status"] == "building":
                matching_files = metadata.repo_map_status.get("matching_files", 0)
                return {
                    "status": "building",
                    "message": "Repository map is being built",
                    "retry_guidance": self._get_retry_guidance(matching_files),
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
                target_files = await self.gather_files(cache_path)

            logger.debug(f"Processing {len(target_files)} files")

            # Check against threshold before proceeding
            file_count = len(target_files)
            effective_threshold = max_files_threshold or DEFAULT_FILES_THRESHOLD
            if file_count > effective_threshold:
                return {
                    "status": "threshold_exceeded",
                    "message": "Number of matching files exceeds processing threshold",
                    "metadata": {
                        "matching_files": file_count,
                        "threshold": effective_threshold,
                        "size_context": f"Large repository ({file_count} matching files)",
                        "override_guidance": "You have several options: 1) Use 'files' or 'directories' parameters to analyze a smaller subset of the codebase, 2) Increase max_files_threshold AND ensure your client timeout is sufficient",
                    },
                }

            # Save complete list before filtering
            all_target_files = target_files.copy()

            # Generate map and process results
            content = repo_map.get_ranked_tags_map([], target_files)

            # Debug output - commented out to avoid file system issues
            # with open("raw_repomap_output.txt", "w", encoding="utf-8") as f:
            #     f.write(str(repo_map))

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
