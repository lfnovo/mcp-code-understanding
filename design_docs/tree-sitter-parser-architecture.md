# Tree-sitter Parser Architecture

## Overview

This document specifies the architecture for a modular, extensible code parsing system using Tree-sitter. The design emphasizes easy addition of new language support while maintaining consistent interfaces and high performance.

## Directory Structure

```
src/code_understanding/
├── parsers/
│   ├── __init__.py
│   ├── base.py                 # Base interfaces
│   ├── tree_sitter/            # Tree-sitter core functionality
│   │   ├── __init__.py
│   │   ├── base_visitor.py     # Abstract syntax tree visitor pattern
│   │   ├── query_builder.py    # Tree-sitter query construction
│   │   └── node_types.py       # Common AST node type definitions
│   ├── languages/              # Language-specific implementations
│   │   ├── __init__.py
│   │   ├── python/
│   │   │   ├── __init__.py
│   │   │   ├── parser.py       # Python-specific parser
│   │   │   ├── visitor.py      # Python AST visitor
│   │   │   └── queries.scm     # Tree-sitter queries for Python
│   │   ├── javascript/         # Future language support
│   │   └── java/              # Future language support
│   └── registry.py            # Parser registry and discovery
```

## Core Components

### 1. Base Parser Interface

The foundation of our parsing system, defining the contract that all language-specific parsers must implement:

```python
class BaseParser(ABC):
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the given file."""
        pass
    
    @abstractmethod
    async def parse_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse a file and return structured information about its contents."""
        pass
```

### 2. Tree-sitter Base Visitor

Implements the visitor pattern for traversing Tree-sitter ASTs with standardized node handling:

```python
class BaseTreeSitterVisitor(ABC):
    @abstractmethod
    def visit_function(self, node, metadata: Dict) -> None:
        """Visit a function definition node."""
        pass
        
    @abstractmethod
    def visit_class(self, node, metadata: Dict) -> None:
        """Visit a class definition node."""
        pass
    
    @abstractmethod
    def visit_import(self, node, metadata: Dict) -> None:
        """Visit an import statement node."""
        pass
    
    def visit(self, tree: "Tree") -> Dict[str, Any]:
        """Entry point for tree traversal."""
        self.result = {
            "functions": [],
            "classes": [],
            "imports": [],
            "dependencies": set(),
            "symbols": {}
        }
        self._traverse(tree.root_node)
        return self.result
```

### 3. Language-specific Parser Implementation

Example of a language-specific parser (Python):

```python
class PythonParser(BaseParser):
    def __init__(self):
        self.language = tree_sitter_languages.get_language('python')
        self.query_builder = QueryBuilder('python')
        self.visitor = PythonVisitor()

    def can_parse(self, file_path: str) -> bool:
        return file_path.endswith('.py')

    async def parse_file(self, content: str, file_path: str) -> Dict[str, Any]:
        tree = self._parse_to_ast(content)
        return self.visitor.visit(tree)

    def _parse_to_ast(self, content: str) -> "Tree":
        parser = Parser()
        parser.set_language(self.language)
        return parser.parse(bytes(content, "utf8"))
```

### 4. Parser Registry

Manages parser discovery and selection:

```python
class ParserRegistry:
    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}
        self._load_parsers()
    
    def _load_parsers(self):
        """Dynamically discover and load parser implementations."""
        parser_dir = Path(__file__).parent / "languages"
        for lang_dir in parser_dir.iterdir():
            if lang_dir.is_dir() and (lang_dir / "parser.py").exists():
                self._load_parser(lang_dir)
    
    def _load_parser(self, lang_dir: Path):
        """Load a specific parser implementation."""
        module = importlib.import_module(f".languages.{lang_dir.name}.parser")
        parser_class = getattr(module, f"{lang_dir.name.capitalize()}Parser")
        self._parsers[lang_dir.name] = parser_class()

    def get_parser(self, file_path: str) -> Optional[BaseParser]:
        """Get appropriate parser for a file."""
        for parser in self._parsers.values():
            if parser.can_parse(file_path):
                return parser
        return None
```

### 5. Query Builder

Manages Tree-sitter queries for efficient AST analysis:

```python
class QueryBuilder:
    def __init__(self, language: str):
        self.language = language
        self._queries: Dict[str, Query] = {}
        self._load_queries()
    
    def _load_queries(self):
        """Load language-specific Tree-sitter queries."""
        query_file = (Path(__file__).parent / "languages" / 
                     self.language / "queries.scm")
        with open(query_file) as f:
            self._raw_queries = f.read()
            self._parse_queries()
    
    def get_query(self, query_name: str) -> Query:
        """Get a compiled Tree-sitter query."""
        return self._queries.get(query_name)
```

## Adding New Language Support

To add support for a new programming language:

1. Create a new directory under `languages/` for the language
2. Implement the language-specific parser and visitor classes
3. Create language-specific Tree-sitter queries in `queries.scm`

Example for adding JavaScript support:

```
languages/javascript/
├── __init__.py
├── parser.py
├── visitor.py
└── queries.scm
```

The parser registry will automatically discover and load the new implementation.

## Benefits

1. **Modularity**: Clear separation between core parsing logic and language-specific implementations
2. **Extensibility**: Easy addition of new language support
3. **Performance**: Efficient parsing through Tree-sitter's native implementation
4. **Consistency**: Standardized AST traversal and query interfaces
5. **Maintainability**: Centralized query management and reusable components

## Dependencies

- tree-sitter
- tree-sitter-{language} (for each supported language)

## Implementation Notes

1. Use async/await for parsing operations to handle large files
2. Cache compiled Tree-sitter queries for performance
3. Implement robust error handling for malformed code
4. Consider memory management for large ASTs
5. Add telemetry for parser performance monitoring
