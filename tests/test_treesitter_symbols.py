import asyncio
from pathlib import Path
import logging
import sys

# Configure logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Import your code
from code_understanding.treesitter.parser import CodeParser


async def test_symbol_extraction():
    """Test that TreeSitter correctly extracts symbols from Python code."""
    # Test Python code with known symbols
    python_code = """
import os
import sys
from typing import List, Dict

def hello_world():
    print("Hello, world!")

class MyClass:
    def __init__(self):
        self.value = 42
        
    def get_value(self):
        return self.value

API_KEY = "secret"
"""

    # Path to query files
    queries_path = Path("src/code_understanding/treesitter/queries")

    # Create parser
    parser = CodeParser(queries_path)

    # Extract symbols
    symbols = await parser.extract_symbols(Path("test.py"), python_code)

    # Print results
    print(f"Found {len(symbols)} symbols:")
    for symbol in symbols:
        print(f"  {symbol['type']}: {symbol['name']} at line {symbol['line']}")

    # Make assertions
    assert len(symbols) > 0, "No symbols extracted!"

    # Check for specific symbols
    function_symbols = [s for s in symbols if s["type"] == "function"]
    class_symbols = [s for s in symbols if s["type"] == "class"]
    import_symbols = [s for s in symbols if s["type"] == "import"]

    print(f"Functions: {len(function_symbols)}")
    print(f"Classes: {len(class_symbols)}")
    print(f"Imports: {len(import_symbols)}")

    assert len(function_symbols) > 0, "No functions found!"
    assert "hello_world" in [
        s["name"] for s in function_symbols
    ], "hello_world function not found"

    assert len(class_symbols) > 0, "No classes found!"
    assert "MyClass" in [s["name"] for s in class_symbols], "MyClass not found"


if __name__ == "__main__":
    asyncio.run(test_symbol_extraction())
