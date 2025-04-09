"""Tree-sitter language detection and registration."""

import os
from typing import Dict, Optional
from pathlib import Path

# Use tree_sitter_language_pack instead of the unmaintained package
from tree_sitter_language_pack import get_language, get_parser


class LanguageRegistry:
    """Manages language detection and Tree-sitter language mappings."""

    # Extension to language mapping
    EXTENSION_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".go": "go",
        # Add more languages as needed
    }

    def __init__(self, queries_path: Path):
        """Initialize with path to query files.

        Args:
            queries_path: Root directory containing language query files
        """
        self.queries_path = Path(queries_path)
        self.languages: Dict[str, object] = {}
        self.parsers: Dict[str, object] = {}

    def detect_language(self, file_path: Path) -> Optional[str]:
        """Detect language from file extension.

        Args:
            file_path: Path to the file

        Returns:
            Language identifier or None if unknown
        """
        ext = file_path.suffix.lower()
        return self.EXTENSION_MAP.get(ext)

    def get_language(self, language_id: str):
        """Get or create a Tree-sitter language.

        Args:
            language_id: Language identifier (e.g., 'python')

        Returns:
            Tree-sitter Language object or None if not supported
        """
        if language_id not in self.languages:
            try:
                self.languages[language_id] = get_language(language_id)
            except Exception:
                return None

        return self.languages[language_id]

    def get_parser(self, language_id: str):
        """Get or create a Tree-sitter parser.

        Args:
            language_id: Language identifier (e.g., 'python')

        Returns:
            Tree-sitter Parser object or None if not supported
        """
        if language_id not in self.parsers:
            try:
                self.parsers[language_id] = get_parser(language_id)
            except Exception:
                return None

        return self.parsers[language_id]

    def get_query_file(self, language: str) -> Optional[Path]:
        """Get Tree-sitter query file for a language.

        Args:
            language: Language identifier

        Returns:
            Path to query file or None if not found
        """
        query_path = self.queries_path / language / "tags.scm"
        return query_path if query_path.exists() else None
