"""
Core search functionality for code understanding.
"""

from typing import Dict, List, Any
import re

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

from ..repository import Repository


class SearchEngine:
    """Handles code search and retrieval functionality.

    This is currently a simple keyword-based implementation, but will be
    enhanced with vector store capabilities in the future.
    """

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
        )

    async def search(self, repo: Repository, query: str) -> Dict[str, Any]:
        """Search the codebase for relevant code snippets.

        This is a temporary implementation until a proper vector store is set up.
        It uses simple keyword matching and ranking.

        Args:
            repo: Repository to search in
            query: Search query string

        Returns:
            Dict containing search results with relevance scores
        """
        relevant_files = await self._find_relevant_files(repo, query)

        if not relevant_files:
            return {"results": [], "total": 0}

        # Process and chunk the relevant files
        documents = []
        for file_path, content in relevant_files:
            doc = Document(page_content=content, metadata={"source": str(file_path)})
            documents.extend(self.text_splitter.split_documents([doc]))

        # Rank chunks by relevance
        ranked_chunks = self._rank_chunks(documents, query)

        # Convert chunks to search results
        results = []
        for chunk in ranked_chunks[:10]:  # Limit to top 10 results
            # Calculate a simple relevance score based on keyword density
            keywords = self._extract_keywords(query)
            content = chunk.page_content.lower()
            total_matches = sum(content.count(keyword) for keyword in keywords)
            max_possible = len(keywords) * (len(content.split()) / 2)  # Rough estimate
            score = min(0.95, total_matches / max_possible) if max_possible > 0 else 0

            results.append(
                {
                    "file": chunk.metadata["source"],
                    "content": chunk.page_content,
                    "score": score,
                    "highlights": self._get_highlights(chunk.page_content, keywords),
                }
            )

        return {"results": results, "total": len(results)}

    async def answer_question(self, repo: Repository, question: str) -> Dict[str, str]:
        """Answer a natural language question about code by finding relevant snippets.

        This method reuses the search functionality but formats results as an answer.
        """
        search_results = await self.search(repo, question)

        if not search_results["results"]:
            return {
                "answer": "I couldn't find any relevant code to answer your question.",
                "sources": [],
            }

        return {
            "answer": "Here are the most relevant code sections I found:",
            "sources": [
                {"file": result["file"], "content": result["content"]}
                for result in search_results["results"][
                    :3
                ]  # Return top 3 most relevant chunks
            ],
        }

    async def _find_relevant_files(
        self, repo: Repository, query: str
    ) -> List[tuple[str, str]]:
        """Find files that might contain information relevant to the query."""
        keywords = self._extract_keywords(query.lower())
        relevant_files = []

        for path in repo.root_path.rglob("*"):
            if not path.is_file() or path.suffix not in [
                ".py",
                ".js",
                ".java",
                ".go",
                ".ts",
            ]:
                continue

            try:
                content = path.read_text()
                if any(keyword in content.lower() for keyword in keywords):
                    relevant_files.append(
                        (str(path.relative_to(repo.root_path)), content)
                    )
            except Exception:
                continue

        return relevant_files

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from the text."""
        # Remove common words and punctuation
        common_words = {
            "what",
            "how",
            "why",
            "where",
            "when",
            "which",
            "is",
            "are",
            "the",
            "in",
            "on",
            "at",
        }
        words = re.findall(r"\w+", text.lower())
        return [w for w in words if w not in common_words and len(w) > 2]

    def _rank_chunks(self, chunks: List[Document], query: str) -> List[Document]:
        """Rank chunks by relevance to the query."""
        keywords = self._extract_keywords(query)

        # Simple ranking based on keyword frequency
        def rank_chunk(chunk: Document) -> int:
            content = chunk.page_content.lower()
            return sum(content.count(keyword) for keyword in keywords)

        return sorted(chunks, key=rank_chunk, reverse=True)

    def _get_highlights(
        self, content: str, keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """Extract snippets of text containing keywords with surrounding context."""
        highlights = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in keywords):
                # Get context (1 line before and after if available)
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                context = "\n".join(lines[start:end])

                highlights.append(
                    {"line_number": i + 1, "context": context}  # 1-based line numbers
                )

        return highlights
