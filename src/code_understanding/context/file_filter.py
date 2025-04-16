"""
File filtering implementation for the Code Understanding service.
Uses PathSpec for .gitignore-style pattern matching and identify for text file detection.
"""

from pathlib import Path
from typing import Union, Dict, List, Optional
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from identify import identify
import logging

logger = logging.getLogger(__name__)

# Directories and files that should be ignored for all languages
# Only include truly common patterns here - not language-specific ones
COMMON_IGNORE_PATTERNS: List[str] = [
    # Directories - need both the directory itself and its contents
    ".aider.*",
    ".git",
    ".git/**",
    ".idea",
    ".idea/**",
    ".vscode",
    ".vscode/**",
    "node_modules",
    "node_modules/**",
    ".vs",
    ".vs/**",
    "tmp",
    "tmp/**",
    "temp",
    "temp/**",
    ".tmp",
    ".tmp/**",
    ".cache",
    ".cache/**",
    ".sass-cache",
    ".sass-cache/**",
    "docs/_build",
    "docs/_build/**",
    "_site",
    "_site/**",
    ".docusaurus",
    ".docusaurus/**",
    "api-docs",
    "api-docs/**",
    "javadoc",
    "javadoc/**",
    "doxygen",
    "doxygen/**",
    # Report and template directories
    "jasperreports",
    "jasperreports/**",
    "jasperreports-legacy",
    "jasperreports-legacy/**",
    # Files
    ".DS_Store",
    "*.log",
    ".env",
    # Configuration and properties files
    "*.properties",
    "*.conf",
    "*.config",
    "*.ini",
    # Security and certificate files
    "*.keystore",
    "*.jks",
    "*.truststore",
    "*.p12",
    # Build and compilation artifacts
    "*.o",
    "*.obj",
    "*.dll",
    "*.so",
    "*.dylib",
    "*.exe",
    "*.out",
    "*.a",
    "*.lib",
    # IDE and editor files
    "*.swp",
    "*.swo",
    "*~",
    "*.bak",
    ".project",
    ".classpath",
    "*.sublime-*",
    "*.suo",
    "*.user",
    "*.workspace",
    "*.cbp",
    # Package lock files
    "yarn.lock",
    "package-lock.json",
    "Gemfile.lock",
    "poetry.lock",
    "Cargo.lock",
    "composer.lock",
    # Database and data files
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.mdb",
    "*.ldb",
    "*.csv",
    "*.dat",
    # Media files
    "*.mp3",
    "*.mp4",
    "*.wav",
    "*.ogg",
    "*.flac",
    "*.avi",
    "*.mov",
    "*.wmv",
    "*.m4a",
    "*.m4v",
    # Archive files
    "*.zip",
    "*.tar",
    "*.gz",
    "*.bz2",
    "*.7z",
    "*.rar",
    "*.iso",
    # Certificate and key files
    "*.pem",
    "*.crt",
    "*.ca-bundle",
    "*.cer",
    "*.p7b",
    "*.p7s",
    "*.pfx",
    "*.key",
    # Office documents
    "*.doc",
    "*.docx",
    "*.xls",
    "*.xlsx",
    "*.ppt",
    "*.pptx",
    "*.odt",
    "*.ods",
    "*.odp",
    # Image files
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.bmp",
    "*.tiff",
    "*.tif",
    "*.ico",
    "*.svg",
    "*.webp",
    "*.psd",
    "*.ai",
    "*.eps",
    "*.raw",
    "*.cr2",
    "*.nef",
    "*.heic",
    "*.heif",
    "*.avif",
    # Font files
    "*.eot",
    "*.ttf",
    "*.woff",
    "*.woff2",
    "*.otf",
    # Document files
    "*.pdf",
    # Image thumbnails and previews
    "*.thumb",
    "*.thumbnail",
    "*_thumb.*",
    "*_preview.*",
    # Image-related metadata
    "*.xmp",  # Adobe metadata
    "Thumbs.db",  # Windows thumbnail cache
    ".picasa.ini",  # Picasa metadata
    # Adobe and design files that often contain images
    "*.indd",  # InDesign
    "*.sketch",  # Sketch App
    "*.fig",  # Figma
    "*.xcf",  # GIMP
    "*.cdr",  # CorelDraw
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
    """Handles file filtering using PathSpec and identify."""

    def __init__(self, language: Optional[str] = None):
        """
        Initialize with optional language-specific patterns.

        Args:
            language: Optional language to include specific ignore patterns
        """
        patterns = COMMON_IGNORE_PATTERNS.copy()
        if language and language in LANGUAGE_IGNORE_PATTERNS:
            patterns.extend(LANGUAGE_IGNORE_PATTERNS[language])
        self.spec = PathSpec.from_lines(GitWildMatchPattern, patterns)

    def _matches_ignore_pattern(self, path: Union[str, Path]) -> bool:
        """Check if path matches any ignore patterns."""
        return self.spec.match_file(str(path))

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

    def should_ignore(self, path: Union[str, Path]) -> bool:
        """
        Determine if a path should be ignored.

        Args:
            path: Path to check

        Returns:
            bool: True if path should be ignored, False otherwise
        """
        # First check against ignore patterns (fast)
        if self._matches_ignore_pattern(path):
            return True

        # If it's a file, check if it's not a text file
        path_obj = Path(path)
        if path_obj.is_file():
            return not self.is_text_file(path)

        return False

    def find_source_files(self, root_dir: Union[str, Path]) -> List[str]:
        """
        Find all source files in directory that aren't ignored.

        Args:
            root_dir: Root directory to search

        Returns:
            List[str]: List of file paths that should be included
        """
        root_path = Path(root_dir)
        result = []

        for path in root_path.rglob("*"):
            if path.is_file() and not self.should_ignore(path):
                result.append(str(path))

        return sorted(result)
