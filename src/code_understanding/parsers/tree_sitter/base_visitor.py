"""
Base visitor for Tree-sitter AST traversal.
Provides a foundation for language-specific visitors.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from tree_sitter import Node, Tree

from .node_types import (
    BaseNode,
    Class,
    Function,
    Import,
    NodeVisitor,
    Position,
    Range,
    SymbolReference,
    Variable
)

class BaseTreeSitterVisitor(NodeVisitor, ABC):
    """Base visitor for Tree-sitter AST nodes.
    
    This class provides the foundation for language-specific Tree-sitter visitors.
    It implements common traversal patterns and node type handling.
    """
    
    def __init__(self):
        self.source_code: str = ""
        self.symbols: Dict[str, SymbolReference] = {}
        self.current_class: Optional[Class] = None
        self.current_function: Optional[Function] = None
    
    def visit_tree(self, tree: Tree, source_code: str) -> Dict[str, Any]:
        """Entry point for tree traversal.
        
        Args:
            tree: Tree-sitter AST
            source_code: Original source code text
            
        Returns:
            Dict containing parsed code structure
        """
        self.source_code = source_code
        self.symbols.clear()
        
        result = {
            'functions': [],
            'classes': [],
            'imports': [],
            'variables': [],
            'symbols': self.symbols
        }
        
        self.visit(tree.root_node)
        return result
    
    def get_node_range(self, node: Node) -> Range:
        """Get the source range for a node."""
        return Range(
            start=Position(node.start_point[0], node.start_point[1]),
            end=Position(node.end_point[0], node.end_point[1])
        )
    
    def get_node_text(self, node: Node) -> str:
        """Get the source text for a node."""
        return self.source_code[node.start_byte:node.end_byte]
    
    @abstractmethod
    def visit_function_definition(self, node: Node) -> Optional[Function]:
        """Visit a function definition node."""
        pass
    
    @abstractmethod
    def visit_class_definition(self, node: Node) -> Optional[Class]:
        """Visit a class definition node."""
        pass
    
    @abstractmethod
    def visit_import(self, node: Node) -> Optional[Import]:
        """Visit an import statement node."""
        pass
    
    @abstractmethod
    def visit_variable(self, node: Node) -> Optional[Variable]:
        """Visit a variable declaration/assignment node."""
        pass
    
    def add_symbol(self, symbol: SymbolReference) -> None:
        """Add a symbol reference to the symbol table."""
        self.symbols[symbol.name] = symbol