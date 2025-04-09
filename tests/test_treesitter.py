"""Test Tree-sitter integration."""

import asyncio
import os
from pathlib import Path

from code_understanding.treesitter.parser import CodeParser
from code_understanding.treesitter.language_registry import LanguageRegistry


async def test_parser():
    """Test Tree-sitter parser with a Python file."""
    # Setup
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    queries_path = (
        project_root / "src" / "code_understanding" / "treesitter" / "queries"
    )

    # Sample Python code
    python_code = """
def hello_world():
    print("Hello, world!")

class MyClass:
    def __init__(self):
        self.value = 42
        
    def get_value(self):
        return self.value

API_KEY = "secret"
"""

    # Parse with Tree-sitter
    parser = CodeParser(queries_path)
    symbols = await parser.extract_symbols(Path("test.py"), python_code)

    # Print results
    print(f"Found {len(symbols)} symbols:")
    for symbol in symbols:
        print(f"{symbol['type']}: {symbol['name']} at line {symbol['line']}")


if __name__ == "__main__":
    asyncio.run(test_parser())
