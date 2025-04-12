"""TreeSitter adapter for the BaseParser interface."""

from typing import Dict, Any
from pathlib import Path

from ..logging_config import logger
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

        logger.debug(f"Parsing {file_path} with TreeSitter (language: {language})")
        logger.debug(f"File size: {len(content)} characters")

        if not language:
            logger.warning(f"Unsupported file type for {file_path}")
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
        logger.debug(f"Starting symbol extraction for {file_path}")
        symbols = await self.parser.extract_symbols(file_path_obj, content)

        if symbols:
            logger.debug(f"✓ Found {len(symbols)} symbols in {file_path}")
        else:
            logger.debug(
                f"✗ No symbols found in {file_path} - check Tree-sitter query patterns"
            )

        logger.debug(f"Extracted {len(symbols)} total symbols from {file_path}")

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
        symbol_counts = {
            "import": 0,
            "class": 0,
            "function": 0,
            "variable": 0,
            "constant": 0,
        }

        for symbol in symbols:
            symbol_type = symbol["type"]
            symbol_name = symbol["name"]
            logger.debug(f"Processing symbol: {symbol_name} (type: {symbol_type})")

            if symbol_type == "import":
                result["imports"].append(
                    {"type": "import", "name": symbol_name, "alias": None}
                )
                symbol_counts["import"] += 1
            elif symbol_type == "class":
                result["classes"].append(
                    {
                        "name": symbol_name,
                        "bases": [],  # Would need deeper analysis
                        "methods": [],  # Would need post-processing
                        "docstring": None,  # Would need post-processing
                    }
                )
                symbol_counts["class"] += 1
            elif symbol_type == "function":
                result["functions"].append(
                    {
                        "name": symbol_name,
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
                symbol_counts["function"] += 1
            elif symbol_type in ["variable", "constant"]:
                result["global_variables"].append(
                    {
                        "name": symbol_name,
                        "value": None,  # Would need deeper analysis
                    }
                )
                symbol_counts[symbol_type] += 1

        # Log summary of extracted symbols
        logger.info(f"Symbol extraction summary for {file_path}:")
        logger.info(f"  - Imports: {symbol_counts['import']}")
        logger.info(f"  - Classes: {symbol_counts['class']}")
        logger.info(f"  - Functions: {symbol_counts['function']}")
        logger.info(f"  - Variables: {symbol_counts['variable']}")
        logger.info(f"  - Constants: {symbol_counts['constant']}")

        if not any(symbol_counts.values()):
            logger.warning(
                f"No symbols were extracted from {file_path} - possible parsing issue"
            )

        return result
