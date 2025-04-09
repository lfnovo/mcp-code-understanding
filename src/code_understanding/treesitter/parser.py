"""Tree-sitter based code parsing and symbol extraction."""

from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import logging

from tree_sitter import Node, Tree

from .language_registry import LanguageRegistry

# Set up logger
logger = logging.getLogger(__name__)


class Symbol:
    """Represents a code symbol with location information."""

    def __init__(
        self,
        name: str,
        type: str,
        start_line: int,
        start_col: int,
        end_line: int,
        end_col: int,
        parent: Optional["Symbol"] = None,
    ):
        self.name = name
        self.type = type
        self.start_line = start_line
        self.start_col = start_col
        self.end_line = end_line
        self.end_col = end_col
        self.parent = parent
        self.children: List[Symbol] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "type": self.type,
            "line": self.start_line,
            "column": self.start_col,
            "end_line": self.end_line,
            "end_column": self.end_col,
        }

        if self.children:
            result["children"] = [child.to_dict() for child in self.children]

        return result


class CodeParser:
    """Handles code parsing and symbol extraction using Tree-sitter."""

    def __init__(self, queries_path: Path):
        """Initialize the parser with path to query files.

        Args:
            queries_path: Path to query files directory
        """
        self.registry = LanguageRegistry(queries_path)

    def _get_text(self, node: Node, content: str) -> str:
        """Extract text from a node.

        Args:
            node: Tree-sitter AST node
            content: Source code string

        Returns:
            Text contained in the node
        """
        start_byte = node.start_byte
        end_byte = node.end_byte
        return content[start_byte:end_byte]

    async def extract_symbols(
        self, file_path: Path, content: str
    ) -> List[Dict[str, Any]]:
        """Extract symbols from code using Tree-sitter.

        Args:
            file_path: Path to the file (used for language detection)
            content: File contents to parse

        Returns:
            List of extracted symbols with locations
        """
        language_id = self.registry.detect_language(file_path)
        if not language_id:
            logger.warning(f"Unsupported file type: {file_path}")
            return []

        # Get language and parser
        language = self.registry.get_language(language_id)
        parser = self.registry.get_parser(language_id)
        if not language or not parser:
            logger.warning(f"Failed to get parser for {language_id}")
            return []

        # Get query file
        query_path = self.registry.get_query_file(language_id)
        if not query_path:
            logger.warning(f"No query file found for {language_id}")
            return []

        try:
            # Parse code
            tree = parser.parse(bytes(content, "utf8"))

            # Load and execute query
            with open(query_path, "r") as f:
                query_string = f.read()

            query = language.query(query_string)
            captures = query.captures(tree.root_node)

            # Process captures into symbols
            symbols = []
            for node, tag_name in captures:
                symbol_type = tag_name.split(".")[-1]  # Extract type from tag
                symbol_name = self._get_text(node, content)

                symbol = {
                    "type": symbol_type,
                    "name": symbol_name,
                    "line": node.start_point[0] + 1,  # Convert to 1-indexed
                    "column": node.start_point[1],
                    "end_line": node.end_point[0] + 1,
                    "end_column": node.end_point[1],
                }
                symbols.append(symbol)

            return symbols

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []
