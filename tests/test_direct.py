import pytest
from pathlib import Path
from tree_sitter_language_pack import get_language, get_parser


def test_tree_sitter_direct():
    """Direct test of tree-sitter functionality without any custom code."""
    # Sample Python code
    code = """
import os

def hello():
    print("Hello")

class Test:
    def method(self):
        pass
"""

    # Convert to bytes
    code_bytes = bytes(code, "utf8")

    # Get language and parser
    python_lang = get_language("python")
    assert python_lang is not None, "Failed to get Python language"

    parser = get_parser("python")
    assert parser is not None, "Failed to get parser"

    # Parse code
    tree = parser.parse(code_bytes)
    assert tree is not None, "Failed to parse code"

    # Create a very simple query
    query_str = "(function_definition) @function"
    query = python_lang.query(query_str)
    assert query is not None, "Failed to create query"

    # Get captures
    captures = query.captures(tree.root_node)
    print(f"Query returned {len(captures)} captures")
    print(f"Type of captures: {type(captures)}")

    # We should have found at least one function
    assert len(captures) > 0, "No captures found"

    # Print all capture entries (for dictionary type)
    print("Capture entries:")
    for key, value in captures.items():
        print(f"  Key: {key} (type: {type(key)})")
        print(f"  Value: {value} (type: {type(value)})")

        # Try to get node
        node = (
            tree.root_node.descendant_for_byte_range(key, key)
            if isinstance(key, int)
            else None
        )
        if node:
            print(f"  Found node: {node}")
            print(f"  Node type: {node.type}")
            print(
                f"  Node text: {code_bytes[node.start_byte:node.end_byte].decode('utf8')}"
            )
