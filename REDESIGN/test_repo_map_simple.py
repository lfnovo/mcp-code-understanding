#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from typing import Set, Union
from aider.io import InputOutput
from aider.repomap import RepoMap

# Common ignore patterns for all languages
COMMON_IGNORE_PATTERNS = {
    "dirs": {
        ".git",
        ".idea",
        ".vscode",
        "node_modules",
        "build",
        "dist",
    },
    "files": {
        ".DS_Store",
        "*.log",
        ".env",
    },
}

# Language-specific ignore patterns
LANGUAGE_IGNORE_PATTERNS = {
    "python": {
        "dirs": {
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".tox",
            ".venv",
            "venv",
            "env",
            ".eggs",
            "*.egg-info",
        },
        "files": {
            "*.pyc",
            "*.pyo",
            "*.pyd",
            "*.so",
            "*.dylib",
            "*.dll",
            "*.coverage",
            ".coverage",
            "coverage.xml",
            ".coveragerc",
            ".python-version",
        },
    },
    "java": {
        "dirs": {
            "target",
            ".settings",
            ".gradle",
            "bin",
            "out",
            ".mvn",
            "generated",
            "generated-sources",
        },
        "files": {
            "*.class",
            "*.jar",
            "*.war",
            "*.ear",
            "*.iml",
            "*.hprof",
            ".classpath",
            ".project",
            ".factorypath",
            "dependency-reduced-pom.xml",
            "*.versionsBackup",
            "mvnw",
            "mvnw.cmd",
        },
    },
}


class IgnorePatterns:
    def __init__(self, languages: Union[str, list] = None):
        """
        Initialize ignore patterns for specified languages.

        Args:
            languages: String or list of strings specifying which language patterns to use.
                      If None, only common patterns are used.
        """
        self.dir_patterns: Set[str] = set(COMMON_IGNORE_PATTERNS["dirs"])
        self.file_patterns: Set[str] = set(COMMON_IGNORE_PATTERNS["files"])

        if languages:
            if isinstance(languages, str):
                languages = [languages]

            for lang in languages:
                if lang in LANGUAGE_IGNORE_PATTERNS:
                    self.dir_patterns.update(LANGUAGE_IGNORE_PATTERNS[lang]["dirs"])
                    self.file_patterns.update(LANGUAGE_IGNORE_PATTERNS[lang]["files"])

    def should_ignore(self, path: Union[str, Path]) -> bool:
        """
        Check if a path should be ignored based on configured patterns.

        Args:
            path: Path to check (string or Path object)

        Returns:
            bool: True if path should be ignored, False otherwise
        """
        if isinstance(path, str):
            path = Path(path)

        # Check directory patterns
        for part in path.parts:
            if any(
                part == pattern
                or (pattern.startswith("*") and part.endswith(pattern[1:]))
                or (pattern.endswith("*") and part.startswith(pattern[:-1]))
                for pattern in self.dir_patterns
            ):
                return True

        # Check file patterns
        filename = path.name
        return any(
            filename == pattern
            or (pattern.startswith("*") and filename.endswith(pattern[1:]))
            or (pattern.endswith("*") and filename.startswith(pattern[:-1]))
            for pattern in self.file_patterns
        )

    @classmethod
    def for_language(cls, language: str) -> "IgnorePatterns":
        """
        Factory method to create an IgnorePatterns instance for a specific language.

        Args:
            language: Language to get ignore patterns for

        Returns:
            IgnorePatterns: Instance configured for the specified language
        """
        return cls(language)


class MinimalModel:
    def token_count(self, text):
        # Rough approximation of token count
        return len(text.split()) * 1.3


class MinimalIO(InputOutput):
    def __init__(self):
        super().__init__()


def find_src_files(root_dir, language="python"):
    """Find all source files in the given directory that match the language."""
    ignore_patterns = IgnorePatterns.for_language(language)
    src_files = []

    # Map language to file extensions
    language_extensions = {"python": [".py"], "java": [".java"]}

    extensions = language_extensions.get(
        language.lower(), [".py"]
    )  # Default to Python if unknown

    for root, _, files in os.walk(root_dir):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                full_path = os.path.join(root, file)
                if not ignore_patterns.should_ignore(Path(full_path)):
                    src_files.append(full_path)

    return src_files


def generate_repo_map(root_dir, language="python", map_tokens=100000):
    """
    Generate a repository map for the given directory.
    """
    io = MinimalIO()
    model = MinimalModel()

    # Create RepoMap instance with files refresh mode
    rm = RepoMap(
        root=root_dir,
        io=io,
        map_tokens=map_tokens,
        main_model=model,
        refresh="files",
    )

    # Get all source files
    src_files = find_src_files(root_dir, language)

    # Generate the map
    repo_map = rm.get_ranked_tags_map([], src_files)

    # Save the repo map output
    with open("repo_map_output.txt", "w") as f:
        f.write(repo_map)


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_repo_map_simple.py <root_dir> [language]")
        sys.exit(1)

    root_dir = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "python"

    if not os.path.isdir(root_dir):
        print(f"Error: {root_dir} is not a directory")
        sys.exit(1)

    generate_repo_map(root_dir, language)
    print("\nRepo map generation complete!")
    print("- repo_map_output.txt: Contains the generated repository map")


if __name__ == "__main__":
    main()
