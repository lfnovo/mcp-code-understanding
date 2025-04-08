"""
Tree-sitter query builder and management.
Provides utilities for building and caching Tree-sitter queries.
"""
from pathlib import Path
from typing import Dict, Optional

from tree_sitter import Language, Query

class QueryBuilder:
    """Manages Tree-sitter queries for a specific language.
    
    This class handles loading, caching, and building Tree-sitter queries
    from .scm files specific to each language.
    """
    
    def __init__(self, language: str, language_object: Language):
        """Initialize query builder for a specific language.
        
        Args:
            language: Language name (e.g., 'python')
            language_object: Tree-sitter Language object
        """
        self.language = language
        self.language_object = language_object
        self._queries: Dict[str, Query] = {}
        self._load_queries()
    
    def _load_queries(self) -> None:
        """Load all query files for the language."""
        query_dir = Path(__file__).parent.parent / 'languages' / self.language / 'queries'
        if not query_dir.exists():
            return
        
        for query_file in query_dir.glob('*.scm'):
            query_name = query_file.stem
            with open(query_file) as f:
                query_content = f.read()
                self._queries[query_name] = Query(
                    self.language_object,
                    query_content
                )
    
    def get_query(self, query_name: str) -> Optional[Query]:
        """Get a compiled query by name.
        
        Args:
            query_name: Name of the query (matches .scm filename)
            
        Returns:
            Compiled Tree-sitter query or None if not found
        """
        return self._queries.get(query_name)
    
    def create_query(self, pattern: str) -> Query:
        """Create a new query from a pattern string.
        
        Args:
            pattern: Tree-sitter query pattern
            
        Returns:
            Compiled Tree-sitter query
        """
        return Query(self.language_object, pattern)
    
    def register_query(self, name: str, query: Query) -> None:
        """Register a query for reuse.
        
        Args:
            name: Name to associate with the query
            query: Compiled Tree-sitter query
        """
        self._queries[name] = query