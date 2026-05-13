from typing import TypedDict, Dict, List, Any


class ContractState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────────────────
    file_path: str
    file_type: str              # "pdf" | "image" | "xml"
    original_filename: str

    # ── Pre-processing ─────────────────────────────────────────────────────
    page_image_paths: List[str]          # enhanced page image paths
    deduplicated_page_indices: List[int] # surviving page indices after dedup

    # ── OCR / Text ─────────────────────────────────────────────────────────
    raw_text_by_page: Dict[int, str]     # page_num → extracted text
    full_text: str                        # concatenated text (all pages)

    # ── Indexing ───────────────────────────────────────────────────────────
    chunks: List[str]
    chunk_metadata: List[Dict[str, Any]] # [{chunk_id, page, source, char_start}]
    session_faiss_ready: bool

    # ── Extraction ─────────────────────────────────────────────────────────
    # field_key → {value, confidence: float, page_ref: int|None, raw_text: str}
    extracted_fields: Dict[str, Dict[str, Any]]

    # ── Output ─────────────────────────────────────────────────────────────
    excel_output_path: str
    errors: List[str]

    # ── Meta ───────────────────────────────────────────────────────────────
    current_step: str
    processing_log: List[str]
