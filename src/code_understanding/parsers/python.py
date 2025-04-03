"""
Python-specific code parser implementation.
"""
from typing import Dict, Any, List
import ast

from .base import BaseParser

class PythonParser(BaseParser):
    def can_parse(self, file_path: str) -> bool:
        return file_path.endswith(".py")
    
    async def parse_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse Python file and extract structural information."""
        try:
            tree = ast.parse(content)
            return {
                "file_path": file_path,
                "type": "python",
                "imports": self._extract_imports(tree),
                "classes": self._extract_classes(tree),
                "functions": self._extract_functions(tree),
                "global_variables": self._extract_global_variables(tree)
            }
        except SyntaxError as e:
            return {
                "file_path": file_path,
                "type": "python",
                "error": f"Syntax error: {str(e)}",
                "imports": [],
                "classes": [],
                "functions": [],
                "global_variables": []
            }
    
    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, str]]:
        """Extract import statements."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append({
                        "type": "import",
                        "name": name.name,
                        "alias": name.asname
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for name in node.names:
                    imports.append({
                        "type": "from_import",
                        "module": module,
                        "name": name.name,
                        "alias": name.asname
                    })
        return imports
    
    def _extract_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract class definitions."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "bases": [self._get_name(base) for base in node.bases],
                    "methods": self._extract_methods(node),
                    "docstring": ast.get_docstring(node)
                })
        return classes
    
    def _extract_methods(self, class_node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Extract methods from a class."""
        methods = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                methods.append({
                    "name": node.name,
                    "args": self._extract_arguments(node),
                    "docstring": ast.get_docstring(node),
                    "decorators": [self._get_name(d) for d in node.decorator_list]
                })
        return methods
    
    def _extract_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract function definitions."""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if this function is inside a class by looking at its ancestors
                parent = node
                is_method = False
                while hasattr(parent, 'parent'):
                    parent = parent.parent
                    if isinstance(parent, ast.ClassDef):
                        is_method = True
                        break
                
                if not is_method:
                    functions.append({
                        "name": node.name,
                        "args": self._extract_arguments(node),
                        "docstring": ast.get_docstring(node),
                        "decorators": [self._get_name(d) for d in node.decorator_list]
                    })
        return functions
    
    def _extract_arguments(self, func_node: ast.FunctionDef) -> Dict[str, Any]:
        """Extract function arguments."""
        args = {
            "positional": [],
            "keyword": [],
            "vararg": None,
            "kwarg": None
        }
        
        for arg in func_node.args.args:
            args["positional"].append({
                "name": arg.arg,
                "annotation": self._get_name(arg.annotation) if arg.annotation else None
            })
        
        for arg in func_node.args.kwonlyargs:
            args["keyword"].append({
                "name": arg.arg,
                "annotation": self._get_name(arg.annotation) if arg.annotation else None
            })
        
        if func_node.args.vararg:
            args["vararg"] = func_node.args.vararg.arg
            
        if func_node.args.kwarg:
            args["kwarg"] = func_node.args.kwarg.arg
            
        return args
    
    def _extract_global_variables(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract global variable assignments."""
        variables = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Check if this assignment is at the module level
                parent = node
                is_local = False
                while hasattr(parent, 'parent'):
                    parent = parent.parent
                    if isinstance(parent, (ast.ClassDef, ast.FunctionDef)):
                        is_local = True
                        break
                
                if not is_local:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            variables.append({
                                "name": target.id,
                                "value": self._get_value(node.value)
                            })
        return variables
    
    def _get_name(self, node: ast.AST) -> str:
        """Get string representation of a name node."""
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)
    
    def _get_value(self, node: ast.AST) -> Any:
        """Get a Python value from an AST node."""
        if isinstance(node, (ast.Str, ast.Bytes)):
            return node.s
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.List):
            return [self._get_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            return {self._get_value(k): self._get_value(v) 
                    for k, v in zip(node.keys, node.values)}
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.NameConstant):
            return node.value
        return None
