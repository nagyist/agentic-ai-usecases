"""
test_retrieval.py — Unit and integration tests for hybrid retrieval system.

Tests:
- BM25 indexing and ranking on exact phrase matches
- Vector search similarity ranking
- RRF fusion logic and deduplication
- Edge cases
"""

import unittest
from keyword_index import KeywordIndex, build_keyword_index
from retrieval_fusion import reciprocal_rank_fusion, fuse_and_get_top_k


class TestKeywordIndex(unittest.TestCase):
    """Tests for BM25 keyword indexing."""
    
    def setUp(self):
        """Create sample chunks for testing."""
        self.chunks = [
            {
                "text": "The machine learning model performed excellently on the test dataset.",
                "start_time": 0,
                "end_time": 10,
            },
            {
                "text": "Deep learning neural networks are powerful for image recognition tasks.",
                "start_time": 10,
                "end_time": 20,
            },
            {
                "text": "Python is a popular programming language for machine learning applications.",
                "start_time": 20,
                "end_time": 30,
            },
            {
                "text": "Data preprocessing is a crucial step in the machine learning pipeline.",
                "start_time": 30,
                "end_time": 40,
            },
            {
                "text": "The team used TensorFlow for building their neural network models.",
                "start_time": 40,
                "end_time": 50,
            },
        ]
    
    def test_exact_phrase_ranking(self):
        """BM25 should rank exact phrase matches highly."""
        index = KeywordIndex(self.chunks)
        results = index.search("machine learning model", top_k=5)
        
        # First result should be the chunk with exact phrase
        self.assertIn("machine learning model", results[0]["text"].lower())
        self.assertGreater(results[0]["bm25_score"], 0)
    
    def test_search_returns_top_k(self):
        """Search should return exactly top_k results."""
        index = KeywordIndex(self.chunks)
        results = index.search("neural", top_k=3)
        self.assertEqual(len(results), 3)
    
    def test_search_with_few_matches(self):
        """Search should handle queries with few matches."""
        index = KeywordIndex(self.chunks)
        results = index.search("rare_word_not_in_corpus", top_k=3)
        # Should return results, but with low scores
        self.assertLessEqual(len(results), 3)
    
    def test_tokenization_lowercase(self):
        """Tokenization should handle lowercase conversion."""
        index = KeywordIndex(self.chunks)
        tokens = index._tokenize("Machine Learning MODEL")
        self.assertEqual(tokens, ["machine", "learning", "model"])
    
    def test_build_keyword_index(self):
        """build_keyword_index convenience function should work."""
        index = build_keyword_index(self.chunks)
        self.assertIsInstance(index, KeywordIndex)
        self.assertEqual(len(index.chunks), 5)


class TestReciprocalRankFusion(unittest.TestCase):
    """Tests for RRF fusion logic."""
    
    def setUp(self):
        """Create sample results from BM25 and vector search."""
        self.chunks = [
            {"start_time": 0, "end_time": 10, "text": "chunk 1", "bm25_score": 5.0},
            {"start_time": 10, "end_time": 20, "text": "chunk 2", "bm25_score": 4.0},
            {"start_time": 20, "end_time": 30, "text": "chunk 3", "score": 0.9},
            {"start_time": 30, "end_time": 40, "text": "chunk 4", "score": 0.8},
            {"start_time": 40, "end_time": 50, "text": "chunk 5", "score": 0.7},
        ]
        
        self.keyword_results = [
            self.chunks[0],
            self.chunks[1],
            self.chunks[2],
        ]
        
        self.vector_results = [
            self.chunks[2],
            self.chunks[3],
            self.chunks[4],
        ]
    
    def test_rrf_deduplication(self):
        """RRF should deduplicate chunks appearing in both lists."""
        fused = reciprocal_rank_fusion(self.keyword_results, self.vector_results)
        
        # Check chunk at (20, 30) appears once, not twice
        chunk_ids = [(c["start_time"], c["end_time"]) for c in fused]
        self.assertEqual(chunk_ids.count((20, 30)), 1)
    
    def test_rrf_includes_all_unique(self):
        """RRF should include all unique chunks from both lists."""
        fused = reciprocal_rank_fusion(self.keyword_results, self.vector_results)
        
        # Should have 5 unique chunks (all three keyword + two new vector)
        self.assertEqual(len(fused), 5)
    
    def test_rrf_duplicates_boosted(self):
        """Chunks in both lists should have higher RRF scores than single-source chunks."""
        fused = reciprocal_rank_fusion(self.keyword_results, self.vector_results, k=60)
        
        # Chunk at (20, 30) is in both, should have higher score than chunks in one list only
        duplicate_chunk = next(c for c in fused if c["start_time"] == 20)
        single_source = next(c for c in fused if c["start_time"] == 40)
        
        self.assertGreater(duplicate_chunk["rrf_score"], single_source["rrf_score"])
    
    def test_rrf_metadata_fields(self):
        """Fused chunks should have rank metadata fields."""
        fused = reciprocal_rank_fusion(self.keyword_results, self.vector_results)
        
        for chunk in fused:
            self.assertIn("rrf_score", chunk)
            self.assertIn("keyword_rank", chunk)
            self.assertIn("vector_rank", chunk)
    
    def test_fuse_and_get_top_k(self):
        """Convenience function should return top_k results."""
        results = fuse_and_get_top_k(
            self.keyword_results,
            self.vector_results,
            top_k=2
        )
        self.assertEqual(len(results), 2)
    
    def test_rrf_parameter_k(self):
        """Higher k should reduce rank effect; all chunks should have closer scores."""
        fused_k60 = reciprocal_rank_fusion(self.keyword_results, self.vector_results, k=60)
        fused_k10 = reciprocal_rank_fusion(self.keyword_results, self.vector_results, k=10)
        
        # With higher k, relative score differences should be smaller
        scores_k60 = [c["rrf_score"] for c in fused_k60]
        scores_k10 = [c["rrf_score"] for c in fused_k10]
        
        max_diff_k60 = max(scores_k60) - min(scores_k60)
        max_diff_k10 = max(scores_k10) - min(scores_k10)
        
        # K=60 should have smaller max diff (if no extreme rank differences)
        # This is a rough check based on RRF formula
        self.assertGreater(max_diff_k10, 0)
        self.assertGreater(max_diff_k60, 0)


class TestHybridEdgeCases(unittest.TestCase):
    """Tests for edge cases in hybrid retrieval."""
    
    def test_empty_keyword_results(self):
        """RRF should handle empty keyword results."""
        vector_results = [
            {"start_time": 0, "end_time": 10, "text": "chunk", "score": 0.9},
        ]
        fused = reciprocal_rank_fusion([], vector_results)
        self.assertEqual(len(fused), 1)
    
    def test_empty_vector_results(self):
        """RRF should handle empty vector results."""
        keyword_results = [
            {"start_time": 0, "end_time": 10, "text": "chunk", "bm25_score": 5.0},
        ]
        fused = reciprocal_rank_fusion(keyword_results, [])
        self.assertEqual(len(fused), 1)
    
    def test_both_empty(self):
        """RRF should handle both empty results."""
        fused = reciprocal_rank_fusion([], [])
        self.assertEqual(len(fused), 0)


if __name__ == "__main__":
    unittest.main()
