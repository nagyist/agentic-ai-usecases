"""
Contract Intelligence System – Streamlit UI
Run: streamlit run app.py
"""

import os
import json
import queue
import tempfile
import threading
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from config.settings import (
    FIELD_DISPLAY_NAMES,
    EXTRACT_FIELDS,
    HIGH_CONFIDENCE,
    LOW_CONFIDENCE,
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
)
from utils.file_utils import get_file_type

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Contract Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; }
    .metric-card {
        background: #f0f4ff; border-radius: 8px;
        padding: 12px 16px; margin: 4px 0;
    }
    .conf-high { color:#006100; background:#C6EFCE; padding:2px 8px;
                 border-radius:4px; font-weight:600; }
    .conf-med  { color:#9C6500; background:#FFEB9C; padding:2px 8px;
                 border-radius:4px; font-weight:600; }
    .conf-low  { color:#9C0006; background:#FFC7CE; padding:2px 8px;
                 border-radius:4px; font-weight:600; }
    .step-done    { color:#28a745; font-weight:600; }
    .step-active  { color:#fd7e14; font-weight:600; }
    .step-pending { color:#6c757d; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Session state defaults ────────────────────────────────────────────────────
def _init_state():
    for key, default in {
        "final_state": None,
        "processing": False,
        "error": None,
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default


_init_state()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _conf_badge(conf: float) -> str:
    if conf >= HIGH_CONFIDENCE:
        return f'<span class="conf-high">🟢 {conf:.0%}</span>'
    if conf >= LOW_CONFIDENCE:
        return f'<span class="conf-med">🟡 {conf:.0%}</span>'
    return f'<span class="conf-low">🔴 {conf:.0%}</span>'


STEP_LABELS = {
    "preprocess":       "Pre-processing",
    "ocr_extract":      "OCR Extraction",
    "detect_language":  "Language Detection",
    "translate":        "Translation",
    "index":            "FAISS + BM25 Indexing",
    "extract":          "Field Extraction (RAG)",
    "generate_excel":   "Excel Generation",
}


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")
    selected_model = st.selectbox(
        "Ollama Model",
        ["qwen2.5vl:7b", "qwen2.5vl:3b"],
        index=0,
        help="Larger model = better accuracy, slower speed",
    )
    ollama_url = st.text_input("Ollama Base URL", value=OLLAMA_BASE_URL)

    st.divider()
    st.markdown("**Supported formats**")
    st.markdown("- 📄 PDF (multi-page)")
    st.markdown("- 🖼️ JPG / PNG / TIFF")
    st.markdown("- 🗂️ XML (generic)")

    st.divider()
    st.markdown("**Extracted fields**")
    for fn in FIELD_DISPLAY_NAMES.values():
        st.markdown(f"• {fn}")



# ── Header ────────────────────────────────────────────────────────────────────
st.title("📄 Contract Intelligence System")
st.caption(
    "Upload a contract → extract key commercial terms via PaddleOCR + "
    "Qwen2.5-VL + hybrid RAG (FAISS + BM25)"
)

# ── Upload ────────────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload Contract",
    type=["pdf", "jpg", "jpeg", "png", "tiff", "xml"],
    help="PDF, image, or XML contract document",
)

if uploaded:
    st.success(f"**{uploaded.name}**  –  {uploaded.size / 1024:.1f} KB")

    col_btn, col_reset = st.columns([3, 1])
    run_clicked = col_btn.button(
        "🚀 Process Contract", type="primary", width="stretch"
    )
    if col_reset.button("🔄 Reset", width="stretch"):
        st.session_state.final_state = None
        st.session_state.error = None
        st.rerun()

    # ── Processing ────────────────────────────────────────────────────────────
    if run_clicked:
        st.session_state.final_state = None
        st.session_state.error = None

        # Validate file type
        try:
            file_type = get_file_type(uploaded.name)
        except ValueError as e:
            st.error(str(e))
            st.stop()

        # Save upload to temp file
        suffix = Path(uploaded.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.getbuffer())
            tmp_path = tmp.name

        # Override settings from sidebar
        os.environ["OLLAMA_MODEL"] = selected_model
        os.environ["OLLAMA_BASE_URL"] = ollama_url

        # Import graph here so env vars are set first
        from graph import contract_graph  # noqa: E402

        initial_state = {
            "file_path": tmp_path,
            "file_type": file_type,
            "original_filename": uploaded.name,
            "page_image_paths": [],
            "deduplicated_page_indices": [],
            "raw_text_by_page": {},
            "full_text": "",
            "detected_language": "en",
            "requires_translation": False,
            "translated_text": "",
            "chunks": [],
            "chunk_metadata": [],
            "session_faiss_ready": False,
            "extracted_fields": {},
            "excel_output_path": "",
            "errors": [],
            "current_step": "preprocessing",
            "processing_log": [],
        }

        # Pipeline progress UI
        st.markdown("### ⚙️ Processing Pipeline")
        step_containers = {}
        step_cols = st.columns(4)
        for i, (step, label) in enumerate(STEP_LABELS.items()):
            col = step_cols[i % 4]
            step_containers[step] = col.empty()
            step_containers[step].markdown(
                f'<span class="step-pending">○ {label}</span>',
                unsafe_allow_html=True,
            )

        progress_bar = st.progress(0, text="Starting…")
        log_area = st.empty()
        ocr_status_area = st.empty()

        # --- Run graph in background thread so we can show per-page OCR progress ---
        from utils.progress import get_queue as _get_ocr_q

        # Drain any stale messages from a previous run
        ocr_q = _get_ocr_q()
        while not ocr_q.empty():
            try:
                ocr_q.get_nowait()
            except queue.Empty:
                break

        _DONE = object()
        steps_q: queue.Queue = queue.Queue()
        error_holder: list = [None]

        def _run_graph():
            try:
                for chunk in contract_graph.stream(initial_state):
                    steps_q.put(chunk)
            except Exception as exc:
                error_holder[0] = str(exc)
            finally:
                steps_q.put(_DONE)

        thread = threading.Thread(target=_run_graph, daemon=True)
        thread.start()

        total_steps = len(STEP_LABELS)
        step_keys = list(STEP_LABELS.keys())
        steps_done = 0
        final_state = None
        graph_done = False
        ocr_page_lines: list[str] = []

        while not graph_done:
            # Drain completed LangGraph steps
            try:
                while True:
                    item = steps_q.get_nowait()
                    if item is _DONE:
                        graph_done = True
                        break
                    step_name = list(item.keys())[0]
                    step_state = list(item.values())[0]
                    steps_done += 1
                    final_state = step_state

                    if step_name in step_containers:
                        step_containers[step_name].markdown(
                            f'<span class="step-done">✅ {STEP_LABELS[step_name]}</span>',
                            unsafe_allow_html=True,
                        )
                    next_idx = (
                        step_keys.index(step_name) + 1
                        if step_name in step_keys
                        else -1
                    )
                    if 0 <= next_idx < len(step_keys):
                        nxt = step_keys[next_idx]
                        step_containers[nxt].markdown(
                            f'<span class="step-active">⏳ {STEP_LABELS[nxt]}</span>',
                            unsafe_allow_html=True,
                        )

                    pct = min(steps_done / total_steps, 1.0)
                    progress_bar.progress(
                        pct,
                        text=f"Completed: {STEP_LABELS.get(step_name, step_name)}",
                    )
                    logs = step_state.get("processing_log", [])
                    if logs:
                        log_area.info("📋 " + logs[-1])

            except queue.Empty:
                pass

            # Drain per-page OCR progress messages
            new_ocr = False
            while not ocr_q.empty():
                try:
                    msg = ocr_q.get_nowait()
                    ocr_page_lines.append(msg)
                    new_ocr = True
                except queue.Empty:
                    break

            if new_ocr and ocr_page_lines:
                # Show last 6 lines so the box doesn't grow too tall
                visible = ocr_page_lines[-6:]
                ocr_status_area.info("🔍 OCR progress\n\n" + "\n\n".join(visible))

            if not graph_done:
                time.sleep(0.25)

        thread.join()

        if error_holder[0]:
            st.session_state.error = error_holder[0]
            progress_bar.empty()

        try:
            os.unlink(tmp_path)
        except OSError:
            pass

        if final_state and not error_holder[0]:
            ocr_status_area.empty()
            progress_bar.progress(1.0, text="✅ Processing complete!")
            st.session_state.final_state = final_state
            st.rerun()

# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.get("error"):
    st.error(f"Processing failed: {st.session_state.error}")

if st.session_state.get("final_state"):
    fs = st.session_state.final_state
    fields = fs.get("extracted_fields", {})
    raw_text = fs.get("raw_text_by_page", {})

    st.divider()
    st.markdown("## 📊 Results")

    # ── Top-level metrics ─────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pages Processed", len(raw_text))
    m2.metric("Chunks Indexed", len(fs.get("chunks", [])))
    m3.metric("Language", fs.get("detected_language", "en").upper())
    found = sum(1 for v in fields.values() if v.get("value"))
    m4.metric("Fields Found", f"{found}/{len(EXTRACT_FIELDS)}")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_fields, tab_rate, tab_raw, tab_log = st.tabs([
        "📋 Extracted Fields",
        "💰 Rate Card",
        "📄 Raw OCR Text",
        "🗒️ Processing Log",
    ])

    # ── Tab 1: Extracted Fields ───────────────────────────────────────────────
    with tab_fields:
        st.subheader("Extracted Contract Fields")

        for key, display in FIELD_DISPLAY_NAMES.items():
            if key == "price_details":
                continue
            fd = fields.get(key, {})
            value = fd.get("value")
            conf = float(fd.get("confidence", 0.0))
            page_ref = fd.get("page_ref", "—")
            raw_snip = fd.get("raw_text", "")

            with st.container():
                c1, c2, c3 = st.columns([2, 5, 1])
                c1.markdown(f"**{display}**")
                if value is not None:
                    c2.markdown(f"`{value}`")
                else:
                    c2.markdown("*Not found*")
                c3.markdown(_conf_badge(conf), unsafe_allow_html=True)

                if raw_snip:
                    with st.expander("Source snippet", expanded=False):
                        st.caption(f"Page {page_ref} · {raw_snip}")

        # Full table view
        st.markdown("---")
        st.markdown("**Full table view**")
        rows = []
        for key, display in FIELD_DISPLAY_NAMES.items():
            if key == "price_details":
                continue
            fd = fields.get(key, {})
            rows.append({
                "Field": display,
                "Value": str(fd.get("value", "")) or "NOT FOUND",
                "Confidence": f"{float(fd.get('confidence', 0)):.0%}",
                "Page": str(fd.get("page_ref", "—")),
            })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    # ── Tab 2: Rate Card ──────────────────────────────────────────────────────
    with tab_rate:
        st.subheader("Price Details / Rate Card")
        pd_data = fields.get("price_details", {})
        items = pd_data.get("value", [])
        conf = float(pd_data.get("confidence", 0.0))
        page_ref = pd_data.get("page_ref", "—")

        col_c, col_p = st.columns(2)
        col_c.markdown(f"**Confidence:** {_conf_badge(conf)}", unsafe_allow_html=True)
        col_p.markdown(f"**Page Reference:** {page_ref}")

        if isinstance(items, list) and items:
            df_rate = pd.DataFrame(items)
            # Rename columns to title case
            df_rate.columns = [c.replace("_", " ").title() for c in df_rate.columns]
            st.dataframe(df_rate, width="stretch", hide_index=True)

            # Raw JSON toggle
            with st.expander("View raw JSON", expanded=False):
                st.json(items)
        elif isinstance(items, str) and items.strip():
            st.text(items)
        else:
            st.info("No rate card data was extracted from this contract.")

    # ── Tab 3: Raw OCR Text ───────────────────────────────────────────────────
    with tab_raw:
        st.subheader("Raw Extracted Text by Page")
        if raw_text:
            for pg_num, text in sorted(raw_text.items()):
                with st.expander(f"Page {pg_num + 1}  ({len(text)} chars)", expanded=False):
                    st.text_area(
                        label=f"Page {pg_num + 1} text",
                        label_visibility="collapsed",
                        value=text,
                        height=300,
                        key=f"raw_page_{pg_num}",
                        disabled=True,
                    )
        else:
            lang = fs.get("detected_language", "en")
            full = fs.get("full_text") or fs.get("translated_text", "")
            st.expander("Full document text", expanded=True).text_area(
                label="Full document text",
                label_visibility="collapsed",
                value=full,
                height=400,
                disabled=True,
            )

    # ── Tab 5: Processing Log ─────────────────────────────────────────────────
    with tab_log:
        st.subheader("Processing Log")
        logs = fs.get("processing_log", [])
        for entry in logs:
            st.markdown(f"• {entry}")

    # ── Excel download ────────────────────────────────────────────────────────
    st.divider()
    excel_path = fs.get("excel_output_path", "")
    if excel_path and Path(excel_path).exists():
        with open(excel_path, "rb") as xf:
            st.download_button(
                label="📥 Download Full Excel Report",
                data=xf.read(),
                file_name=Path(excel_path).name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
                type="primary",
            )
        st.caption(
            "Excel contains 3 sheets: Extracted Fields · Rate Card · Raw OCR Text"
        )

elif not uploaded:
    st.info("👆 Upload a contract document to get started.")
