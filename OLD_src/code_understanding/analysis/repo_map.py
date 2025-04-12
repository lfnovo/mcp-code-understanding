"""
Repository mapping analysis using Aider's RepoMap functionality.
"""

from pathlib import Path
from typing import List
import io
from contextlib import redirect_stdout, redirect_stderr

from aider.io import InputOutput
from aider.models import Model
from aider.repomap import RepoMap
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from ..config import ContextConfig
from ..repository import Repository


class SilentIO(InputOutput):
    """Custom IO class that suppresses all output from Aider."""

    def __init__(self):
        super().__init__()
        self.silent = True

    def tool_error(self, *args, **kwargs):
        """Suppress tool errors"""
        pass

    def info(self, *args, **kwargs):
        """Suppress info messages"""
        pass

    def system(self, *args, **kwargs):
        """Suppress system messages"""
        pass

    def warn(self, *args, **kwargs):
        """Suppress warning messages"""
        pass


class RepoMapAnalyzer:
    def __init__(self, config: ContextConfig):
        self.io = SilentIO()
        self.model = Model("gpt-3.5-turbo")
        self.config = config

        # Default ignore patterns setup with pathspec
        self.default_ignore_patterns = [
            # Version Control
            ".git/",
            ".hg/",
            ".svn/",
            # Python
            "*.py[cod]",
            "__pycache__/",
            "*.so",
            "*.egg",
            "*.egg-info/",
            "dist/",
            "build/",
            "eggs/",
            "parts/",
            "bin/",
            "var/",
            "sdist/",
            "develop-eggs/",
            ".installed.cfg",
            "lib/",
            "lib64/",
            "venv/",
            ".venv/",
            "env/",
            ".env/",
            ".Python",
            # Node/JavaScript
            "node_modules/",
            "bower_components/",
            "*.min.js",
            "*.min.css",
            # Java
            "*.class",
            "*.jar",
            "*.war",
            "*.ear",
            "target/",
            ".gradle/",
            "build/",
            # IDE
            ".idea/",
            ".vscode/",
            "*.swp",
            "*.swo",
            ".project",
            ".classpath",
            ".settings/",
            # OS
            ".DS_Store",
            "Thumbs.db",
        ]

        self.pathspec = PathSpec.from_lines(
            GitWildMatchPattern, self.default_ignore_patterns
        )

    def should_ignore(self, path: Path) -> bool:
        """
        Check if a path should be ignored using pathspec.
        This handles both default patterns and .gitignore if present
        """
        return self.pathspec.match_file(str(path))

    async def analyze_repository(self, repo: Repository) -> str:
        """
        Analyze repository using Aider's RepoMap functionality.
        Returns a structured string representation optimized for LLM consumption.
        """
        # Update pathspec with .gitignore if present
        gitignore_path = repo.root_path / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path) as f:
                additional_patterns = f.readlines()
                self.pathspec = PathSpec.from_lines(
                    GitWildMatchPattern,
                    self.default_ignore_patterns + additional_patterns,
                )

        # Create RepoMap with configuration matching test script
        repo_map = RepoMap(
            main_model=self.model,
            root=str(repo.root_path),
            io=self.io,
            verbose=False,  # Ensure verbose is False
            map_tokens=100000,  # 100k tokens for comprehensive map
            map_mul_no_files=1,  # Don't multiply token limit
            refresh="always",  # Always generate fresh map
        )

        # Collect non-ignored files
        files = [
            str(path)
            for path in repo.root_path.rglob("*")
            if path.is_file()
            and not repo.is_ignored(path.relative_to(repo.root_path))
            and not self.should_ignore(path)
        ]

        # Capture and suppress any stdout/stderr from Aider
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            # Generate and return the repo map
            return repo_map.get_repo_map([], files)
