"""
retrieval_fusion.py — Reciprocal Rank Fusion (RRF) for hybrid search.

Merges keyword (BM25) and semantic (vector) results into a single ranked list.
Uses reciprocal rank fusion formula: score = sum(1 / (rank + k))
"""

from typing import List, Dict, Tuple


def reciprocal_rank_fusion(
    keyword_results: List[Dict],
    vector_results: List[Dict],
    k: int = 60,
) -> List[Dict]:
    """
    Merge and rank results from keyword and vector searches using RRF.
    
    RRF formula for each result:
        score = sum(1 / (rank_keyword + k) + 1 / (rank_vector + k))
    
    Where rank is 0-indexed position in each result list.
    Results appearing in both lists get scores from both; results in one list only
    contribute their single score.
    
    Args:
        keyword_results: List of chunks from BM25 search (with 'bm25_score' field)
        vector_results: List of chunks from vector search (with 'score' field for cosine similarity)
        k: RRF parameter; higher k diminishes effect of rank position
           Default 60 is standard; tune based on result quality
    
    Returns:
        List of unique chunks sorted by fused RRF score (descending)
        Each chunk has 'rrf_score', 'keyword_rank', 'vector_rank' fields added
    """
    
    # Build ranking maps: chunk_id -> (rank, original_chunk_dict)
    # Using (start_time, end_time) as unique chunk ID
    keyword_ranks: Dict[Tuple, Tuple[int, Dict]] = {}
    vector_ranks: Dict[Tuple, Tuple[int, Dict]] = {}
    
    for rank, chunk in enumerate(keyword_results):
        chunk_id = (chunk.get("start_time"), chunk.get("end_time"))
        keyword_ranks[chunk_id] = (rank, chunk)
    
    for rank, chunk in enumerate(vector_results):
        chunk_id = (chunk.get("start_time"), chunk.get("end_time"))
        vector_ranks[chunk_id] = (rank, chunk)
    
    # Compute RRF scores for all unique chunks
    rrf_scores: Dict[Tuple, float] = {}
    all_chunks: Dict[Tuple, Dict] = {}
    chunk_metadata: Dict[Tuple, Dict] = {}  # Track rank info
    
    # Process keyword results
    for chunk_id, (rank, chunk) in keyword_ranks.items():
        rrf_scores[chunk_id] = 1.0 / (rank + k)
        all_chunks[chunk_id] = chunk
        chunk_metadata[chunk_id] = {"keyword_rank": rank, "vector_rank": None}
    
    # Process vector results
    for chunk_id, (rank, chunk) in vector_ranks.items():
        vector_contribution = 1.0 / (rank + k)
        if chunk_id in rrf_scores:
            rrf_scores[chunk_id] += vector_contribution
            chunk_metadata[chunk_id]["vector_rank"] = rank
        else:
            rrf_scores[chunk_id] = vector_contribution
            all_chunks[chunk_id] = chunk
            chunk_metadata[chunk_id] = {"keyword_rank": None, "vector_rank": rank}
    
    # Sort by RRF score descending
    sorted_chunks = sorted(
        all_chunks.items(),
        key=lambda item: rrf_scores[item[0]],
        reverse=True
    )
    
    # Build result list with metadata
    results = []
    for chunk_id, chunk in sorted_chunks:
        result_chunk = chunk.copy()
        result_chunk["rrf_score"] = rrf_scores[chunk_id]
        result_chunk["keyword_rank"] = chunk_metadata[chunk_id]["keyword_rank"]
        result_chunk["vector_rank"] = chunk_metadata[chunk_id]["vector_rank"]
        results.append(result_chunk)
    
    return results


def fuse_and_get_top_k(
    keyword_results: List[Dict],
    vector_results: List[Dict],
    top_k: int = 5,
    rrf_k: int = 60,
) -> List[Dict]:
    """
    Convenience function: fuse results and return top_k.
    
    Args:
        keyword_results: BM25 search results
        vector_results: Vector search results
        top_k: Number of results to return from fused list
        rrf_k: RRF parameter
        
    Returns:
        Top k chunks from fused ranking
    """
    fused = reciprocal_rank_fusion(keyword_results, vector_results, k=rrf_k)
    return fused[:top_k]
