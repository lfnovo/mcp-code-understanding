"""
File filtering implementation for the Code Understanding service.
Uses PathSpec for .gitignore-style pattern matching.
"""

from pathlib import Path
from typing import Union, Dict, List, Optional
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

# Directories and files that should be ignored for all languages
# Only include truly common patterns here - not language-specific ones
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
        "build/**",  # These are Python-specific
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
        "target/**",  # Java-specific
        ".settings",
        ".settings/**",
        "bin",
        "bin/**",
        "build",
        "build/**",  # Java also uses build
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

    def __init__(
        self,
        languages: Optional[Union[str, List[str]]] = None,
        use_common_patterns: bool = True,
        use_language_patterns: bool = True,
    ):
        """Initialize with optional language-specific patterns and filtering options.

        Args:
            languages: Optional language(s) to use for language-specific patterns
            use_common_patterns: Whether to use common ignore patterns
            use_language_patterns: Whether to use language-specific patterns
        """
        # Store languages for reference
        if isinstance(languages, str):
            self.languages = [languages]
        else:
            self.languages = languages or []

        self.use_common_patterns = use_common_patterns
        self.use_language_patterns = use_language_patterns

        # Set up ignore patterns based on configuration
        ignore_patterns = []
        if use_common_patterns:
            ignore_patterns.extend(COMMON_IGNORE_PATTERNS)

        # Always include ALL language patterns when use_language_patterns is True
        if use_language_patterns:
            for lang_patterns in LANGUAGE_IGNORE_PATTERNS.values():
                ignore_patterns.extend(lang_patterns)

        # Create PathSpec objects
        self.ignore_spec = PathSpec.from_lines(GitWildMatchPattern, ignore_patterns)

        # Load .gitignore if it exists
        self.gitignore_spec = None

    def _load_gitignore(self, root_dir: Union[str, Path]) -> Optional[PathSpec]:
        """Load .gitignore patterns if the file exists.

        Args:
            root_dir: Repository root directory

        Returns:
            PathSpec object with .gitignore patterns, or None if file doesn't exist
        """
        gitignore_path = Path(root_dir) / ".gitignore"
        if not gitignore_path.exists():
            return None

        try:
            with open(gitignore_path, "r") as f:
                patterns = f.readlines()
            return PathSpec.from_lines(GitWildMatchPattern, patterns)
        except Exception as e:
            logger.warning(f"Failed to load .gitignore: {e}")
            return None

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

        # Check .gitignore patterns first if they exist
        if self.gitignore_spec and self.gitignore_spec.match_file(path_str):
            return True

        # Then check our ignore patterns
        return self.ignore_spec.match_file(path_str)

    def find_source_files(self, root_dir: Union[str, Path]) -> List[str]:
        """Find all non-ignored source files in the directory."""
        root_path = Path(root_dir)

        # Load .gitignore patterns if they exist
        self.gitignore_spec = self._load_gitignore(root_path)

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
