"""
File filtering implementation for the Code Understanding service.
Uses PathSpec for .gitignore-style pattern matching.
"""

from pathlib import Path
from typing import Union, Dict, List, Optional
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

# Directories and files that should be ignored for all languages
COMMON_IGNORE_PATTERNS: List[str] = [
    # Directories - need both the directory itself and its contents
    ".git",
    ".git/**",
    ".idea",
    ".idea/**",
    ".vscode",
    ".vscode/**",
    "node_modules",
    "node_modules/**",
    # Files
    ".DS_Store",
    "*.log",
    ".env",
]

# Language-specific ignore patterns
LANGUAGE_IGNORE_PATTERNS: Dict[str, List[str]] = {
    "python": [
        "__pycache__",
        "__pycache__/**",
        ".pytest_cache",
        ".pytest_cache/**",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".Python",
        "env",
        "env/**",
        "venv",
        "venv/**",
        ".env",
        ".venv",
        ".venv/**",
        "ENV",
        "ENV/**",
        "build",
        "build/**",
        "develop-eggs",
        "develop-eggs/**",
        "dist",
        "dist/**",
        "downloads",
        "downloads/**",
        "eggs",
        "eggs/**",
        "lib",
        "lib/**",
        "lib64",
        "lib64/**",
        "parts",
        "parts/**",
        "sdist",
        "sdist/**",
        "var",
        "var/**",
        "wheels",
        "wheels/**",
        "*.egg-info",
        "*.egg-info/**",
        ".installed.cfg",
        "*.egg",
    ],
    "java": [
        "target",
        "target/**",
        ".settings",
        ".settings/**",
        "bin",
        "bin/**",
        "build",
        "build/**",
        "*.class",
        "*.jar",
        "*.war",
        "*.ear",
        "*.logs",
        "*.iml",
        ".gradle",
        ".gradle/**",
    ],
}

# Language-specific file extensions to include
LANGUAGE_EXTENSIONS: Dict[str, List[str]] = {
    "python": ["*.py"],
    "java": ["*.java"],
}


class FileFilter:
    """PathSpec-based file filtering."""

    def __init__(self, languages: Optional[Union[str, List[str]]] = None):
        """Initialize with optional language-specific patterns."""
        # Store languages for reference
        if isinstance(languages, str):
            self.languages = [languages]
        else:
            self.languages = languages or []

        # Set up ignore patterns
        ignore_patterns = list(COMMON_IGNORE_PATTERNS)  # Always use common patterns

        # Only add language-specific patterns for the specified languages
        if self.languages:
            for lang in self.languages:
                if lang in LANGUAGE_IGNORE_PATTERNS:
                    ignore_patterns.extend(LANGUAGE_IGNORE_PATTERNS[lang])

        # Set up include patterns
        include_patterns = []
        if self.languages:
            for lang in self.languages:
                if lang in LANGUAGE_EXTENSIONS:
                    include_patterns.extend(LANGUAGE_EXTENSIONS[lang])

        # Create PathSpec objects
        self.ignore_spec = PathSpec.from_lines(GitWildMatchPattern, ignore_patterns)
        self.include_spec = (
            PathSpec.from_lines(GitWildMatchPattern, include_patterns)
            if include_patterns
            else None
        )

    @classmethod
    def for_language(cls, language: str) -> "FileFilter":
        """Factory method to create a language-specific filter."""
        return cls(language)

    def should_ignore(self, path: Union[str, Path], is_dir: bool = None) -> bool:
        """
        Check if a file or directory should be ignored.

        Args:
            path: The path to check
            is_dir: Whether the path is a directory (if None, will be determined from the path)

        Returns:
            True if the path should be ignored, False otherwise
        """
        # Convert to string and normalize path separators
        if isinstance(path, Path):
            path_str = path.as_posix()
        else:
            path_str = Path(path).as_posix()

        # Determine if it's a directory if not specified
        if is_dir is None:
            p = Path(path)
            is_dir = p.is_dir() if p.exists() else path_str.endswith("/")

        # For directories: only use ignore patterns
        if is_dir:
            return self.ignore_spec.match_file(path_str)

        # For files:
        # - If it matches an include pattern, KEEP IT regardless of ignore patterns
        # - Otherwise, check against ignore patterns
        if self.include_spec and self.include_spec.match_file(path_str):
            return False  # KEEP files that match include patterns

        # If no include patterns OR file doesn't match include patterns, check ignore patterns
        return self.ignore_spec.match_file(path_str)

    def find_source_files(self, root_dir: Union[str, Path]) -> List[str]:
        """Find all non-ignored source files in the directory."""
        root_path = Path(root_dir)
        source_files = []

        # Use os.walk for more control over directory traversal
        import os

        for dirpath, dirnames, filenames in os.walk(root_path):
            rel_dirpath = os.path.relpath(dirpath, root_path)
            if rel_dirpath == ".":
                rel_dirpath = ""

            # Remove ignored directories from dirnames to prevent traversal
            # This modifies dirnames in-place to affect the walk
            i = 0
            while i < len(dirnames):
                dir_path = (
                    os.path.join(rel_dirpath, dirnames[i])
                    if rel_dirpath
                    else dirnames[i]
                )
                if self.should_ignore(dir_path, is_dir=True):
                    dirnames.pop(i)
                else:
                    i += 1

            # Add non-ignored files
            for filename in filenames:
                file_path = (
                    os.path.join(rel_dirpath, filename) if rel_dirpath else filename
                )
                if not self.should_ignore(file_path, is_dir=False):
                    source_files.append(os.path.join(dirpath, filename))

        return sorted(source_files)
