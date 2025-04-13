"""
Repository path handling utilities.
"""

import hashlib
import re
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import urlparse


def is_git_url(path: str) -> bool:
    """Check if a path is a Git URL."""
    if not path:
        return False

    # Handle SSH URLs
    if path.startswith("git@"):
        return True

    # Handle HTTPS URLs
    try:
        parsed = urlparse(path)
        return parsed.scheme in ("http", "https") and (
            parsed.netloc == "github.com" or "git" in parsed.netloc
        )
    except Exception:
        return False


def parse_github_url(url: str) -> Tuple[str, str, Optional[str]]:
    """Parse a GitHub URL into org, repo, and optional ref."""
    # Handle SSH URLs
    if url.startswith("git@github.com:"):
        path = url.split("git@github.com:")[1]
    else:
        # Handle HTTPS URLs
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")

    # Split path into parts
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {url}")

    org = parts[0]

    # Handle .git extension and refs
    repo_part = parts[1]
    if repo_part.endswith(".git"):
        repo = repo_part[:-4]
    else:
        repo = repo_part

    # Check for ref (branch, tag, commit)
    ref = None
    if len(parts) > 2:
        ref = "/".join(parts[2:])

    return org, repo, ref


def get_cache_path(cache_dir: Path, repo_path: str) -> Path:
    """Get deterministic cache path for a repository."""
    # Ensure cache_dir is absolute
    cache_dir = Path(cache_dir).resolve()

    if is_git_url(repo_path):
        # For GitHub URLs
        try:
            org, repo, ref = parse_github_url(repo_path)
            # Include ref in hash if present
            url_hash = hashlib.sha256(repo_path.encode()).hexdigest()[:8]
            return (cache_dir / "github" / org / f"{repo}-{url_hash}").resolve()
        except ValueError:
            # Fall back to generic git handling
            url_hash = hashlib.sha256(repo_path.encode()).hexdigest()[:8]
            return (cache_dir / "git" / url_hash).resolve()
    else:
        # For local paths
        abs_path = str(Path(repo_path).resolve())
        path_hash = hashlib.sha256(abs_path.encode()).hexdigest()[:8]
        return (cache_dir / "local" / path_hash).resolve()
