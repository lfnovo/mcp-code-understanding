# debug_tree_sitter.py
from tree_sitter_language_pack import get_language, get_parser
import json


def explore_tree_sitter():
    print("Tree-sitter debug exploration")

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

    try:
        # Get Python language and parser
        python_lang = get_language("python")
        parser = get_parser("python")

        # Parse code
        tree = parser.parse(code_bytes)
        root = tree.root_node

        # Print the root node
        print(f"Root node: {root.type}")

        # Explore direct children
        print("Root node children:")
        for i, child in enumerate(root.children):
            print(f"  Child {i}: {child.type}")

            # Print more details for important node types
            if child.type == "function_definition":
                print(f"    Function details:")
                for j, func_child in enumerate(child.children):
                    print(f"      Part {j}: {func_child.type}")

            elif child.type == "class_definition":
                print(f"    Class details:")
                for j, class_child in enumerate(child.children):
                    print(f"      Part {j}: {class_child.type}")

        # Try a very simple query
        print("\nTesting query:")
        query_str = "(function_definition) @func"
        query = python_lang.query(query_str)
        captures = query.captures(root)

        print(f"Captures type: {type(captures)}")
        print(f"Captures count: {len(captures)}")

        if isinstance(captures, dict):
            print("Dictionary captures:")
            for key, value in captures.items():
                print(f"  {key}: {value}")
        else:
            print("List captures:")
            for cap in captures:
                print(f"  {cap}")

        # Try walking the tree recursively
        print("\nFound symbols by manual traversal:")
        functions = []
        classes = []

        def visit_node(node, depth=0):
            indent = "  " * depth
            node_text = code_bytes[node.start_byte : node.end_byte].decode("utf8")
            print(
                f"{indent}{node.type}: {node_text[:30]}{'...' if len(node_text) > 30 else ''}"
            )

            # Check for functions
            if node.type == "function_definition":
                # Find name
                for child in node.children:
                    if child.type == "identifier":
                        name = code_bytes[child.start_byte : child.end_byte].decode(
                            "utf8"
                        )
                        functions.append(
                            {"name": name, "line": child.start_point[0] + 1}
                        )
                        break

            # Check for classes
            if node.type == "class_definition":
                # Find name
                for child in node.children:
                    if child.type == "identifier":
                        name = code_bytes[child.start_byte : child.end_byte].decode(
                            "utf8"
                        )
                        classes.append({"name": name, "line": child.start_point[0] + 1})
                        break

            # Visit children
            for child in node.children:
                visit_node(child, depth + 1)

        visit_node(root)

        print("\nFunctions found by traversal:")
        for func in functions:
            print(f"  {func['name']} at line {func['line']}")

        print("\nClasses found by traversal:")
        for cls in classes:
            print(f"  {cls['name']} at line {cls['line']}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    explore_tree_sitter()
