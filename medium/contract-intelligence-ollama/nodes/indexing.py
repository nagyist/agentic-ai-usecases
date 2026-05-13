from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from models.state import ContractState
from services.vector_store import HybridVectorStore
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP

# Reset per document — no cross-document persistence.
_session_store: HybridVectorStore | None = None


def get_session_store() -> HybridVectorStore:
    return _session_store  # type: ignore[return-value]


def _find_page(chunk: str, raw_text_by_page: Dict[int, str]) -> int:
    """Best-effort page number for a chunk (0-indexed)."""
    needle = chunk[:60].strip()
    for pg, pg_text in raw_text_by_page.items():
        if needle in pg_text:
            return pg
    return 0


def indexing_node(state: ContractState) -> dict:
    global _session_store
    log = list(state.get("processing_log", []))

    # Prefer translated text when available
    text = state.get("translated_text") or state.get("full_text", "")
    raw_text_by_page = state.get("raw_text_by_page", {})
    source_name = state.get("original_filename", "contract")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "; ", ", ", " "],
    )
    chunks: List[str] = splitter.split_text(text)

    metadata: List[Dict[str, Any]] = [
        {
            "chunk_id": i,
            "page": _find_page(chunk, raw_text_by_page),
            "source": source_name,
        }
        for i, chunk in enumerate(chunks)
    ]

    _session_store = HybridVectorStore()
    _session_store.add_documents(chunks, metadata)

    log.append(f"Indexed {len(chunks)} chunks into session FAISS+BM25")
    return {
        **state,
        "chunks": chunks,
        "chunk_metadata": metadata,
        "session_faiss_ready": True,
        "processing_log": log,
        "current_step": "extraction",
    }
