"""
File filtering implementation for the Code Understanding service.
Uses extension-based inclusion and identify for text file detection.
"""

from pathlib import Path
from typing import Union, Set, List
from identify import identify
import logging

logger = logging.getLogger(__name__)


class FileFilter:
    """Handles file filtering using extension inclusion and text file verification."""

    def __init__(self):
        """Initialize with allowed extensions from resources file."""
        self.allowed_extensions = self._load_extensions()

    def _load_extensions(self) -> Set[str]:
        """
        Load allowed extensions from the language_extensions.txt resource file.

        Returns:
            Set[str]: Set of allowed file extensions (including the dot)
        """
        resource_path = (
            Path(__file__).parent.parent / "resources" / "language_extensions.txt"
        )
        try:
            with open(resource_path, "r", encoding="utf-8") as f:
                # Extensions in file already include the dot
                return {line.strip() for line in f if line.strip()}
        except Exception as e:
            logger.error(f"Failed to load language extensions: {e}")
            return set()

    def is_text_file(self, path: Union[str, Path]) -> bool:
        """
        Check if a file is a text file using identify.

        Args:
            path: Path to the file to check

        Returns:
            bool: True if file is text, False otherwise
        """
        try:
            tags = identify.tags_from_path(str(path))
            return "text" in tags
        except Exception as e:
            logger.debug(f"identify failed for {path}: {e}")
            return False

    def should_include(self, path: Union[str, Path]) -> bool:
        """
        Determine if a file should be included based on extension and text content.

        Args:
            path: Path to check

        Returns:
            bool: True if file should be included, False otherwise
        """
        path_obj = Path(path)
        if not path_obj.is_file():
            return False

        # Check extension first (fast operation)
        if path_obj.suffix.lower() not in self.allowed_extensions:
            return False

        # Then verify it's a text file
        return self.is_text_file(path_obj)

    def find_source_files(self, root_dir: Union[str, Path]) -> List[str]:
        """
        Find all source files in directory that should be included.

        Args:
            root_dir: Root directory to search

        Returns:
            List[str]: List of file paths that should be included
        """
        root_path = Path(root_dir)
        result = []
        total_files = 0

        for path in root_path.rglob("*"):
            if path.is_file():
                total_files += 1
                if self.should_include(path):
                    result.append(str(path))

        logger.debug(
            f"File filtering results - Total files: {total_files}, "
            f"Files matching extension and text criteria: {len(result)}"
        )
        return sorted(result)
