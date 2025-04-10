"""Tree-sitter based code parsing and symbol extraction."""

from typing import Dict, Any, List, Optional
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

    def _find_name_node(self, node: Node) -> Optional[Node]:
        """Find the name identifier within a definition node.

        Args:
            node: Parent definition node

        Returns:
            Name node or None if not found
        """
        # Look for the identifier child node
        for child in node.children:
            if child.type == "identifier":
                return child
        return None

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
            logger.debug(f"Successfully parsed file into Tree-sitter AST")

            # Load and execute query
            logger.debug(f"Loading query file from {query_path}")
            with open(query_path, "r") as f:
                query_string = f.read()
            logger.debug(f"Loaded query ({len(query_string)} bytes)")

            query = language.query(query_string)
            logger.debug("Successfully created Tree-sitter query")

            # Process captures into symbols
            symbols = []
            try:
                captures = query.captures(tree.root_node)
                logger.debug(f"Query execution complete, processing captures")

                if isinstance(captures, dict):
                    # Handle dictionary format with arrays of nodes
                    for capture_type, nodes in captures.items():
                        if isinstance(nodes, list):
                            for node in nodes:
                                try:
                                    # Find the name node
                                    name_node = self._find_name_node(node)

                                    if not name_node:
                                        logger.debug(
                                            f"Couldn't find name for {capture_type} node"
                                        )
                                        continue

                                    symbol_name = self._get_text(name_node, content)
                                    logger.debug(
                                        f"Found symbol: {symbol_name} ({capture_type})"
                                    )

                                    symbol = {
                                        "type": capture_type,
                                        "name": symbol_name,
                                        "line": name_node.start_point[0]
                                        + 1,  # Convert to 1-indexed
                                        "column": name_node.start_point[1],
                                        "end_line": name_node.end_point[0] + 1,
                                        "end_column": name_node.end_point[1],
                                    }
                                    symbols.append(symbol)
                                except Exception as e:
                                    logger.error(f"Error processing node: {e}")
                                    continue
                        else:
                            logger.warning(
                                f"Expected list for capture type {capture_type}, got {type(nodes)}"
                            )
                else:
                    # Handle standard tree-sitter format (list of tuples)
                    for capture in captures:
                        try:
                            node, tag_name = capture

                            # Find the name node
                            name_node = self._find_name_node(node)

                            if not name_node:
                                logger.debug(f"Couldn't find name for {tag_name} node")
                                continue

                            symbol_name = self._get_text(name_node, content)
                            logger.debug(f"Found symbol: {symbol_name} ({tag_name})")

                            symbol = {
                                "type": tag_name,
                                "name": symbol_name,
                                "line": name_node.start_point[0]
                                + 1,  # Convert to 1-indexed
                                "column": name_node.start_point[1],
                                "end_line": name_node.end_point[0] + 1,
                                "end_column": name_node.end_point[1],
                            }
                            symbols.append(symbol)
                        except Exception as e:
                            logger.error(f"Error processing capture: {e}")
                            continue
            except Exception as e:
                logger.error(f"Error processing captures: {e}")

            logger.debug(f"Extracted {len(symbols)} symbols total")
            return symbols

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []
