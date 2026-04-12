"""
embedder.py - Embed transcript chunks and build a FAISS index
"""

import numpy as np
import faiss
import pickle
import os
from openai import OpenAI


EMBEDDING_MODEL = "text-embedding-3-small"
EMBED_BATCH_SIZE = 64


def get_embeddings(texts: list[str], client: OpenAI) -> np.ndarray:
    """Embed a list of texts using OpenAI embeddings in batches."""
    all_embeddings = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i:i + EMBED_BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)
    return np.array(all_embeddings, dtype=np.float32)


def build_index(chunks: list[dict], client: OpenAI) -> tuple[faiss.Index, list[dict]]:
    """
    Build a FAISS flat L2 index from transcript chunks.
    Returns (index, chunks) — chunks are stored as metadata alongside index.
    """
    texts = [c["text"] for c in chunks]
    embeddings = get_embeddings(texts, client)

    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / (norms + 1e-10)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product = cosine after normalization
    index.add(embeddings)

    return index, chunks


def search_index(
    query: str,
    index: faiss.Index,
    chunks: list[dict],
    client: OpenAI,
    top_k: int = 5,
) -> list[dict]:
    """
    Search the FAISS index for chunks most relevant to query.
    Returns top_k chunks with similarity scores.
    """
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
    q_emb = np.array([response.data[0].embedding], dtype=np.float32)
    # Normalize
    q_emb = q_emb / (np.linalg.norm(q_emb) + 1e-10)

    scores, indices = index.search(q_emb, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(chunks):
            chunk = chunks[idx].copy()
            chunk["score"] = float(score)
            results.append(chunk)
    return results
