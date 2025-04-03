"""
Question answering engine for code understanding.
"""
from typing import Dict, List, Any
import re

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

from .repository import Repository

class QAEngine:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
    
    async def answer_question(self, repo: Repository, question: str) -> Dict[str, str]:
        """Answer a natural language question about the codebase."""
        # For MVP, implement simple keyword-based search
        relevant_files = await self._find_relevant_files(repo, question)
        
        if not relevant_files:
            return {
                "answer": "I couldn't find any relevant code to answer your question.",
                "sources": []
            }
        
        # Process and chunk the relevant files
        documents = []
        for file_path, content in relevant_files:
            doc = Document(
                page_content=content,
                metadata={"source": str(file_path)}
            )
            documents.extend(self.text_splitter.split_documents([doc]))
        
        # For MVP, return the most relevant chunks based on keyword matching
        relevant_chunks = self._rank_chunks(documents, question)
        
        return {
            "answer": "Here are the most relevant code sections I found:",
            "sources": [
                {
                    "file": chunk.metadata["source"],
                    "content": chunk.page_content
                }
                for chunk in relevant_chunks[:3]  # Return top 3 most relevant chunks
            ]
        }
    
    async def _find_relevant_files(self, repo: Repository, question: str) -> List[tuple[str, str]]:
        """Find files that might contain information relevant to the question."""
        keywords = self._extract_keywords(question.lower())
        relevant_files = []
        
        for path in repo.root_path.rglob("*"):
            if not path.is_file() or path.suffix not in [".py", ".js", ".java", ".go", ".ts"]:
                continue
            
            try:
                content = path.read_text()
                if any(keyword in content.lower() for keyword in keywords):
                    relevant_files.append((
                        str(path.relative_to(repo.root_path)),
                        content
                    ))
            except Exception:
                continue
        
        return relevant_files
    
    def _extract_keywords(self, question: str) -> List[str]:
        """Extract relevant keywords from the question."""
        # Remove common words and punctuation
        common_words = {"what", "how", "why", "where", "when", "which", "is", "are", "the", "in", "on", "at"}
        words = re.findall(r'\w+', question.lower())
        return [w for w in words if w not in common_words and len(w) > 2]
    
    def _rank_chunks(self, chunks: List[Document], question: str) -> List[Document]:
        """Rank chunks by relevance to the question."""
        keywords = self._extract_keywords(question)
        
        # Simple ranking based on keyword frequency
        def rank_chunk(chunk: Document) -> int:
            content = chunk.page_content.lower()
            return sum(content.count(keyword) for keyword in keywords)
        
        return sorted(chunks, key=rank_chunk, reverse=True)
