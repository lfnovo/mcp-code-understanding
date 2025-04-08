"""
Common AST node types and structures for Tree-sitter parsing.
These types represent the common elements found across different programming languages.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

@dataclass
class Position:
    """Source code position information."""
    line: int
    column: int

@dataclass
class Range:
    """Source code range with start and end positions."""
    start: Position
    end: Position

@dataclass
class BaseNode:
    """Base class for all AST nodes."""
    node_type: str
    range: Range
    text: str

@dataclass
class Function(BaseNode):
    """Function definition node."""
    name: str
    parameters: List[str]
    return_type: Optional[str] = None
    decorators: List[str] = None
    body: List[BaseNode] = None
    docstring: Optional[str] = None

@dataclass
class Class(BaseNode):
    """Class definition node."""
    name: str
    bases: List[str]
    methods: List[Function] = None
    decorators: List[str] = None
    docstring: Optional[str] = None

@dataclass
class Import(BaseNode):
    """Import statement node."""
    module: str
    names: List[str]  # imported names
    is_from: bool = False
    alias: Optional[str] = None

@dataclass
class Variable(BaseNode):
    """Variable declaration/assignment node."""
    name: str
    value_type: Optional[str] = None
    is_constant: bool = False

@dataclass
class SymbolReference:
    """Reference to a symbol in code."""
    name: str
    kind: str  # 'function', 'class', 'variable', etc.
    location: Range
    definition: Optional[BaseNode] = None

class NodeVisitor:
    """Base visitor interface for traversing AST nodes."""
    
    def visit(self, node: Any) -> None:
        """Visit a node and dispatch to the appropriate method."""
        method = f'visit_{node.node_type}'
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node: Any) -> None:
        """Called for nodes that don't have a specific visitor method."""
        pass