"""TreeSitter adapter for the BaseParser interface."""

from typing import Dict, Any
from pathlib import Path

from .base import BaseParser
from ..treesitter.parser import CodeParser


class TreeSitterParser(BaseParser):
    """Adapter to use Tree-sitter CodeParser with the BaseParser interface."""

    def __init__(self, queries_path: Path):
        """Initialize TreeSitter parser.

        Args:
            queries_path: Path to query files
        """
        self.parser = CodeParser(queries_path)

    def can_parse(self, file_path: str) -> bool:
        """Check if file can be parsed by TreeSitter.

        Args:
            file_path: Path to file

        Returns:
            True if file can be parsed
        """
        language = self.parser.registry.detect_language(Path(file_path))
        return language is not None

    async def parse_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse file using TreeSitter.

        Args:
            content: File content
            file_path: Path to file

        Returns:
            Parsed file structure
        """
        file_path_obj = Path(file_path)
        language = self.parser.registry.detect_language(file_path_obj)

        if not language:
            return {
                "file_path": file_path,
                "type": "unknown",
                "error": "Unsupported file type",
                "imports": [],
                "classes": [],
                "functions": [],
                "global_variables": [],
            }

        # Extract symbols
        symbols = await self.parser.extract_symbols(file_path_obj, content)

        # Convert to expected format
        result = {
            "file_path": file_path,
            "type": language,
            "imports": [],
            "classes": [],
            "functions": [],
            "global_variables": [],
        }

        # Group symbols by type
        for symbol in symbols:
            if symbol["type"] == "import":
                result["imports"].append(
                    {"type": "import", "name": symbol["name"], "alias": None}
                )
            elif symbol["type"] == "class":
                result["classes"].append(
                    {
                        "name": symbol["name"],
                        "bases": [],  # Would need deeper analysis
                        "methods": [],  # Would need post-processing
                        "docstring": None,  # Would need post-processing
                    }
                )
            elif symbol["type"] == "function":
                result["functions"].append(
                    {
                        "name": symbol["name"],
                        "args": {
                            "positional": [],
                            "keyword": [],
                            "vararg": None,
                            "kwarg": None,
                        },
                        "docstring": None,
                        "decorators": [],
                    }
                )
            elif symbol["type"] == "variable" or symbol["type"] == "constant":
                result["global_variables"].append(
                    {
                        "name": symbol["name"],
                        "value": None,  # Would need deeper analysis
                    }
                )

        return result
