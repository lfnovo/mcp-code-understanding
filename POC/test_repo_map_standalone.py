#!/usr/bin/env python3

import os
import sys
from pathlib import Path

from aider.repomap import RepoMap
from aider.io import InputOutput
from aider.models import Model


def should_ignore(path):
    """
    Check if a path should be ignored based on common Python project patterns.
    """
    # Common Python ignore patterns
    ignore_dir_patterns = {
        "__pycache__",
        ".git",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        ".venv",
        "venv",
        "env",
        "build",
        "dist",
        "node_modules",
        ".idea",
        ".vscode",
        ".eggs",
        "*.egg-info",
    }

    # Common file patterns to ignore
    ignore_file_patterns = {
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".DS_Store",
        "*.so",
        "*.dylib",
        "*.dll",
        "*.coverage",
        ".coverage",
        "coverage.xml",
        ".coveragerc",
        ".python-version",
        ".env",
        "*.log",
    }

    # Convert path to parts for checking
    parts = Path(path).parts

    # Check directory patterns
    for part in parts:
        if any(
            part == pattern or part.endswith(".egg-info")
            for pattern in ignore_dir_patterns
        ):
            return True

    # Check file patterns
    filename = parts[-1]
    return any(
        filename == pattern
        or (pattern.startswith("*.") and filename.endswith(pattern[1:]))
        for pattern in ignore_file_patterns
    )


def main():
    if len(sys.argv) != 2:
        print("Usage: ./test_repo_map_standalone.py <directory_path>")
        print("Example: ./test_repo_map_standalone.py /path/to/your/code")
        sys.exit(1)

    # Get the directory to analyze from command line
    root_dir = os.path.abspath(sys.argv[1])
    if not os.path.isdir(root_dir):
        print(f"Error: {root_dir} is not a directory")
        sys.exit(1)

    print(f"Analyzing directory: {root_dir}")

    # Find all Python files in the specified directory and subdirectories
    python_files = []
    ignored_dirs = set()
    ignored_files = set()

    for root, dirs, files in os.walk(root_dir):
        # Remove ignored directories in-place to prevent walking into them
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d))]

        for file in files:
            if not file.endswith(".py"):
                continue

            full_path = os.path.join(root, file)
            if should_ignore(full_path):
                ignored_files.add(full_path)
                continue

            python_files.append(full_path)

    print(f"Found {len(python_files)} Python files to analyze")
    if ignored_files:
        print(f"Ignored {len(ignored_files)} Python files in ignored paths")

    # Create the minimum required components, exactly as proven in the test
    io = InputOutput()
    model = Model("gpt-3.5-turbo")

    # Initialize RepoMap with a much larger token limit
    repo_map = RepoMap(
        main_model=model,
        root=root_dir,
        io=io,
        verbose=True,
        map_tokens=100000,  # Increased to 100k tokens to get a comprehensive map
        map_mul_no_files=1,  # Don't multiply the token limit when no files in chat
        refresh="always",  # Always generate a fresh map
    )

    # Get the repo map - using the exact same pattern as the test
    # First argument [] means no files in chat context
    # Second argument is our list of files to analyze
    result = repo_map.get_repo_map([], python_files)

    # Save the output to a file so we can examine it
    output_file = "repo_map_output.txt"
    with open(output_file, "w") as f:
        f.write(result)

    print(f"\nRepo map has been generated and saved to {output_file}")
    print(f"Output file size: {os.path.getsize(output_file)} bytes")

    # Clean up as done in the test
    del repo_map


if __name__ == "__main__":
    main()
