import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from repo root (two levels up from this file)
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TEMP_DIR = DATA_DIR / "temp"
OUTPUT_DIR = DATA_DIR / "output"

for _d in [DATA_DIR, TEMP_DIR, OUTPUT_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Embeddings
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Child chunk size — small for retrieval precision; parent (full page) goes to LLM
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100

# Search — how many child chunks to retrieve before expanding to parent pages
TOP_K_RETRIEVAL = 8
RRF_K = 60

# Confidence thresholds
HIGH_CONFIDENCE = 0.80
LOW_CONFIDENCE = 0.50

# OCR DPI for PDF conversion
PDF_DPI = 200

EXTRACT_FIELDS = [
    "supplier_legal_name",
    "receiver_legal_entity",
    "start_date",
    "end_date",
    "price_details",
    "payment_term",
    "price_validity_period",
]

FIELD_DISPLAY_NAMES = {
    "supplier_legal_name": "Supplier Legal Name",
    "receiver_legal_entity": "Receiver Legal Entity",
    "start_date": "Start Date",
    "end_date": "End Date",
    "price_details": "Price Details (Rate Card)",
    "payment_term": "Payment Term",
    "price_validity_period": "Price Validity Period",
}
