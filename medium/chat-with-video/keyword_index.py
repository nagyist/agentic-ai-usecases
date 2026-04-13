"""
keyword_index.py — BM25 keyword indexing and retrieval for transcript chunks.

Provides efficient keyword-based search as complement to semantic vector search.
"""

from rank_bm25 import BM25Okapi
from typing import List, Dict


class KeywordIndex:
    """Build and search a BM25 keyword index from transcript chunks."""
    
    def __init__(self, chunks: List[Dict]):
        """
        Initialize BM25 index from chunks.
        
        Args:
            chunks: List of chunk dicts with 'text', 'start_time', 'end_time' keys
        """
        self.chunks = chunks
        self.corpus = [chunk["text"] for chunk in chunks]
        # Tokenize: split on whitespace, lowercase, simple punctuation removal
        self.tokenized_corpus = [self._tokenize(text) for text in self.corpus]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
    
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple tokenization: lowercase, split on whitespace."""
        import re
        # Convert to lowercase, split on whitespace, remove punctuation
        tokens = re.findall(r'\w+', text.lower())
        return tokens
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search BM25 index for chunks matching query.
        
        Args:
            query: Search query string
            top_k: Number of top results to return
            
        Returns:
            List of chunks with 'bm25_score' added; sorted by score descending
        """
        query_tokens = self._tokenize(query)
        
        # BM25 returns scores for each document in corpus
        scores = self.bm25.get_scores(query_tokens)
        
        # Sort by score descending, get top_k indices
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]
        
        results = []
        for idx in top_indices:
            if idx < len(self.chunks):
                chunk = self.chunks[idx].copy()
                chunk["bm25_score"] = float(scores[idx])
                results.append(chunk)
        
        return results


def build_keyword_index(chunks: List[Dict]) -> KeywordIndex:
    """
    Convenience function to build a BM25 index from chunks.
    
    Args:
        chunks: List of chunk dicts
        
    Returns:
        KeywordIndex instance ready for search
    """
    return KeywordIndex(chunks)
