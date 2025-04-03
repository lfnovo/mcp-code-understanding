"""
Base parser interface for language-specific code parsers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseParser(ABC):
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the given file."""
        pass
    
    @abstractmethod
    async def parse_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse a file and return structured information about its contents."""
        pass
