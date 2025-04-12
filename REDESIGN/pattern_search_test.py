#!/usr/bin/env python3

import argparse
import fnmatch
import json
import os
import re
from typing import Dict, List, Optional, Set

# Common patterns to exclude for Python and Java projects
DEFAULT_EXCLUDE_DIRS = {
    # Python
    "venv/",
    "env/",
    ".env/",
    ".venv/",
    "__pycache__/",
    "*.pyc",
    ".pytest_cache/",
    ".coverage",
    "htmlcov/",
    "dist/",
    "build/",
    "*.egg-info/",
    ".tox/",
    # Java
    "target/",
    "build/",
    ".gradle/",
    "out/",
    "bin/",
    ".settings/",
    ".idea/",
    "*.class",
    "*.jar",
    "*.war",
    # Common VCS directories
    ".git/",
    ".svn/",
    ".hg/",
    # IDE and editor files
    ".vscode/",
    ".idea/",
    "*.swp",
    "*.swo",
    ".DS_Store",
    "Thumbs.db",
}


def should_skip_path(path: str, exclude_patterns: Set[str]) -> bool:
    """
    Check if a path should be skipped based on exclude patterns.

    Args:
        path: Path to check
        exclude_patterns: Set of glob patterns to exclude

    Returns:
        True if path should be skipped, False otherwise
    """
    path_parts = path.split(os.sep)

    for pattern in exclude_patterns:
        # Check each part of the path against the pattern
        for part in path_parts:
            if fnmatch.fnmatch(part, pattern.rstrip("/")):
                return True

        # Also check the full path
        if fnmatch.fnmatch(path, pattern):
            return True

    return False


def search_codebase(
    root_dir: str,
    search_pattern: str,
    file_pattern: Optional[str] = None,
    ignore_case: bool = False,
    max_results: Optional[int] = None,
    exclude_patterns: Optional[Set[str]] = None,
) -> List[Dict]:
    """
    Search codebase for pattern matches.

    Args:
        root_dir: Root directory to search
        search_pattern: Regex pattern to search for
        file_pattern: Optional glob pattern to filter files
        ignore_case: Whether to ignore case in pattern matching
        max_results: Optional limit on number of results
        exclude_patterns: Optional set of glob patterns to exclude

    Returns:
        List of matches with file path, line number and content
    """
    flags = re.IGNORECASE if ignore_case else 0
    pattern = re.compile(search_pattern, flags)
    matches = []

    # Use default exclude patterns if none provided
    if exclude_patterns is None:
        exclude_patterns = DEFAULT_EXCLUDE_DIRS

    for root, dirs, files in os.walk(root_dir):
        # Skip excluded directories
        dirs[:] = [
            d
            for d in dirs
            if not should_skip_path(os.path.join(root, d), exclude_patterns)
        ]

        for file in files:
            # Skip excluded files
            if should_skip_path(os.path.join(root, file), exclude_patterns):
                continue

            # Apply file pattern filter if specified
            if file_pattern and not fnmatch.fnmatch(file, file_pattern):
                continue

            path = os.path.join(root, file)
            rel_path = os.path.relpath(path, root_dir)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            match = {
                                "file": rel_path,
                                "line": i,
                                "content": line.strip(),
                            }
                            matches.append(match)

                            if max_results and len(matches) >= max_results:
                                return matches

            except (UnicodeDecodeError, PermissionError):
                continue  # Skip binary/inaccessible files

    return matches


def main():
    parser = argparse.ArgumentParser(description="Search codebase for pattern matches")
    parser.add_argument("root_dir", help="Root directory to search")
    parser.add_argument("pattern", help="Search pattern (regex)")
    parser.add_argument("--file-pattern", help="Glob pattern to filter files")
    parser.add_argument(
        "--ignore-case", action="store_true", help="Ignore case in pattern matching"
    )
    parser.add_argument(
        "--max-results", type=int, help="Maximum number of results to return"
    )
    parser.add_argument(
        "--output", default="search_results.json", help="Output JSON file"
    )
    parser.add_argument(
        "--no-exclude", action="store_true", help="Disable default exclusion patterns"
    )
    parser.add_argument(
        "--exclude",
        action="append",
        help="Additional patterns to exclude (can be specified multiple times)",
    )

    args = parser.parse_args()

    # Set up exclude patterns
    exclude_patterns = set()
    if not args.no_exclude:
        exclude_patterns.update(DEFAULT_EXCLUDE_DIRS)
    if args.exclude:
        exclude_patterns.update(args.exclude)

    # Perform search
    results = search_codebase(
        args.root_dir,
        args.pattern,
        args.file_pattern,
        args.ignore_case,
        args.max_results,
        exclude_patterns,
    )

    # Save results
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(
            {
                "search_pattern": args.pattern,
                "file_pattern": args.file_pattern,
                "ignore_case": args.ignore_case,
                "max_results": args.max_results,
                "exclude_patterns": list(exclude_patterns),
                "total_matches": len(results),
                "matches": results,
            },
            f,
            indent=2,
        )

    print(f"Found {len(results)} matches. Results saved to {args.output}")


if __name__ == "__main__":
    main()
