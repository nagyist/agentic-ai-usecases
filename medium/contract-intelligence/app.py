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

    /* Confidence badges — light mode */
    .conf-high { color:#1a5c1a; background:#d4edda; padding:3px 10px;
                 border-radius:12px; font-weight:600; font-size:0.85rem; }
    .conf-med  { color:#7a5000; background:#fff3cd; padding:3px 10px;
                 border-radius:12px; font-weight:600; font-size:0.85rem; }
    .conf-low  { color:#842029; background:#f8d7da; padding:3px 10px;
                 border-radius:12px; font-weight:600; font-size:0.85rem; }

    /* Confidence badges — dark mode */
    @media (prefers-color-scheme: dark) {
        .conf-high { color:#a3d9a5; background:#1a3d1a; }
        .conf-med  { color:#ffe08a; background:#3d3000; }
        .conf-low  { color:#f5a5aa; background:#3d1015; }
    }

    /* Pipeline step indicators */
    .step-done    { color:#28a745; font-weight:600; font-size:0.88rem; }
    .step-active  { color:#fd7e14; font-weight:600; font-size:0.88rem; }
    .step-pending { color:#6c757d; font-size:0.88rem; }

    /* Welcome hero card */
    .hero-card {
        border: 1px solid rgba(128,128,128,0.2);
        border-radius: 12px;
        padding: 28px 32px;
        margin: 16px 0;
        background: linear-gradient(135deg, rgba(99,102,241,0.06) 0%, rgba(168,85,247,0.04) 100%);
    }
    .hero-card h3 { margin-top: 0; }
    .hero-step {
        display: inline-flex; align-items: center; gap: 8px;
        background: rgba(128,128,128,0.08); border-radius: 8px;
        padding: 8px 14px; margin: 4px 6px 4px 0; font-size: 0.9rem;
    }
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

def _fmt_page_ref(page_ref) -> str:
    if page_ref is None:
        return "—"
    if isinstance(page_ref, list):
        return ", ".join(str(p) for p in page_ref)
    return str(page_ref)


def _conf_badge(conf: float) -> str:
    if conf >= HIGH_CONFIDENCE:
        return f'<span class="conf-high">🟢 {conf:.0%}</span>'
    if conf >= LOW_CONFIDENCE:
        return f'<span class="conf-med">🟡 {conf:.0%}</span>'
    return f'<span class="conf-low">🔴 {conf:.0%}</span>'


STEP_LABELS = {
    "preprocess":       "Pre-processing",
    "ocr_extract":      "OCR Extraction",
    "index":            "FAISS + BM25 Indexing",
    "extract":          "Field Extraction (RAG)",
    "generate_excel":   "Excel Generation",
}


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("ℹ️ About")

    st.divider()
    st.markdown("**Supported formats**")
    st.markdown("- 📄 PDF (multi-page)\n- 🖼️ JPG / PNG / TIFF\n- 🗂️ XML (generic)")

    st.divider()
    st.markdown("**Extracted fields**")
    st.markdown("\n".join(f"- {fn}" for fn in FIELD_DISPLAY_NAMES.values()))



# ── Header ────────────────────────────────────────────────────────────────────
st.title("📄 Contract Intelligence System")
st.caption(
    "Upload a contract → extract key commercial terms via PaddleOCR + "
    "OpenAI GPT-4o + hybrid RAG (FAISS + BM25)"
)

# ── Upload ────────────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload Contract",
    type=["pdf", "jpg", "jpeg", "png", "tiff", "xml"],
    help="PDF, image, or XML contract document",
)

if uploaded:
    st.success(f"**{uploaded.name}**  –  {uploaded.size / 1024:.1f} KB")

    # ── OCR cache detection ───────────────────────────────────────────────────
    from utils.ocr_cache import find_cached_ocr
    cached_xlsx = find_cached_ocr(uploaded.name)
    skip_ocr = False
    if cached_xlsx:
        st.info(
            f"💾 Existing OCR output found: **{cached_xlsx.name}**  \n"
            "Enable the toggle below to reuse it and skip the 5–10 min OCR step."
        )
        skip_ocr = st.toggle(
            "Skip OCR — reuse Raw OCR Text from existing Excel",
            value=True,
            key="skip_ocr_toggle",
        )

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

        # Import graph here so env vars are set first
        from graph import contract_graph  # noqa: E402

        # Pre-load OCR from cache if the user opted in
        cached_raw_text: dict = {}
        cached_full_text: str = ""
        if skip_ocr and cached_xlsx:
            from utils.ocr_cache import load_ocr_from_excel
            try:
                cached_raw_text, cached_full_text = load_ocr_from_excel(cached_xlsx)
            except Exception as exc:
                st.warning(f"Could not load cached OCR ({exc}). Running full OCR.")
                cached_raw_text, cached_full_text = {}, ""

        initial_state = {
            "file_path": tmp_path,
            "file_type": file_type,
            "original_filename": uploaded.name,
            "page_image_paths": [],
            "deduplicated_page_indices": [],
            "raw_text_by_page": cached_raw_text,
            "full_text": cached_full_text,
            "chunks": [],
            "chunk_metadata": [],
            "session_faiss_ready": False,
            "extracted_fields": {},
            "excel_output_path": "",
            "errors": [],
            "current_step": "preprocessing",
            "processing_log": [],
            "prompt_log": [],
        }

        # Pipeline progress UI
        st.markdown("### ⚙️ Processing Pipeline")
        step_containers = {}
        step_cols = st.columns(len(STEP_LABELS))
        for i, (step, label) in enumerate(STEP_LABELS.items()):
            col = step_cols[i]
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
    m1, m2, m3 = st.columns(3)
    m1.metric("Pages Processed", len(raw_text))
    m2.metric("Chunks Indexed", len(fs.get("chunks", [])))
    found = sum(1 for v in fields.values() if v.get("value"))
    m3.metric("Fields Found", f"{found}/{len(EXTRACT_FIELDS)}")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_fields, tab_rate, tab_raw, tab_prompt, tab_log = st.tabs([
        "📋 Extracted Fields",
        "💰 Rate Card",
        "📄 Raw OCR Text",
        "🔍 Prompt Log",
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
            page_ref = _fmt_page_ref(fd.get("page_ref"))
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
                "Page": _fmt_page_ref(fd.get("page_ref")),
            })
        st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

    # ── Tab 2: Rate Card ──────────────────────────────────────────────────────
    with tab_rate:
        st.subheader("Price Details / Rate Card")
        pd_data = fields.get("price_details", {})
        items = pd_data.get("value", [])
        conf = float(pd_data.get("confidence", 0.0))
        page_ref = _fmt_page_ref(pd_data.get("page_ref"))

        col_c, col_p = st.columns(2)
        col_c.markdown(f"**Confidence:** {_conf_badge(conf)}", unsafe_allow_html=True)
        col_p.markdown(f"**Page Reference:** {page_ref}")

        if isinstance(items, list) and items:
            df_rate = pd.DataFrame(items)
            st.dataframe(df_rate, width='stretch', hide_index=True)

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
            full = fs.get("full_text", "")
            st.expander("Full document text", expanded=True).text_area(
                label="Full document text",
                label_visibility="collapsed",
                value=full,
                height=400,
                disabled=True,
            )

    # ── Tab 4: Prompt Log ─────────────────────────────────────────────────────
    with tab_prompt:
        st.subheader("Prompt Log — Per-Attribute Extraction Details")
        prompt_log = fs.get("prompt_log", [])

        if not prompt_log:
            st.info("No prompt log available. Re-run the pipeline to capture extraction details.")
        else:
            # Summary token table
            summary_rows = []
            for entry in prompt_log:
                if "page_calls" in entry:
                    in_tok = sum(c["input_tokens"] for c in entry.get("page_calls", []))
                    out_tok = sum(c["output_tokens"] for c in entry.get("page_calls", []))
                else:
                    in_tok = entry.get("input_tokens", 0)
                    out_tok = entry.get("output_tokens", 0)
                summary_rows.append({
                    "Attribute": entry.get("display_name", entry.get("attribute", "")),
                    "Function": entry.get("function", ""),
                    "RAG Queries": len(entry.get("rag_queries", [])),
                    "Chunks Retrieved": len(entry.get("top_k_chunks", [])),
                    "Input Tokens": in_tok,
                    "Output Tokens": out_tok,
                    "Total Tokens": in_tok + out_tok,
                })
            st.markdown("**Token Usage Summary**")
            st.dataframe(pd.DataFrame(summary_rows), width='stretch', hide_index=True)

            st.divider()
            st.markdown("**Per-Attribute Details**")

            for entry in prompt_log:
                attr = entry.get("display_name", entry.get("attribute", ""))
                fn = entry.get("function", "")

                with st.expander(f"**{attr}**  —  `{fn}`", expanded=False):
                    # Metadata row
                    is_price = "page_calls" in entry
                    if is_price:
                        page_calls = entry.get("page_calls", [])
                        canon_call = entry.get("canon_call", {})
                        in_tok = sum(c["input_tokens"] for c in page_calls) + canon_call.get("input_tokens", 0)
                        out_tok = sum(c["output_tokens"] for c in page_calls) + canon_call.get("output_tokens", 0)
                    else:
                        in_tok = entry.get("input_tokens", 0)
                        out_tok = entry.get("output_tokens", 0)

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Attribute", attr)
                    m2.metric("Function", fn)
                    m3.metric("Input Tokens", in_tok)
                    m4.metric("Output Tokens", out_tok)

                    if entry.get("error"):
                        st.error(f"Error during extraction: {entry['error']}")
                        continue

                    # RAG Queries
                    st.markdown("**RAG Queries**")
                    for i, q in enumerate(entry.get("rag_queries", []), 1):
                        st.markdown(f"{i}. `{q}`")

                    # Top-K Chunks
                    st.markdown("**Top-K Retrieved Chunks**")
                    chunks_data = entry.get("top_k_chunks", [])
                    if chunks_data:
                        def _retrieval_source(c):
                            has_faiss = c.get("faiss_rank") is not None
                            has_bm25 = c.get("bm25_rank") is not None
                            if has_faiss and has_bm25:
                                return "FAISS + BM25"
                            if has_faiss:
                                return "FAISS only"
                            if has_bm25:
                                return "BM25 only"
                            return "—"

                        def _fmt_rank(r):
                            return str(int(r) + 1) if r is not None else "—"

                        df_chunks = pd.DataFrame([
                            {
                                "#": i + 1,
                                "Page": c["page"],
                                "Retrieved By": _retrieval_source(c),
                                "Semantic Rank": _fmt_rank(c.get("faiss_rank")),
                                "BM25 Rank": _fmt_rank(c.get("bm25_rank")),
                                "RRF Score": c["score"],
                                "Text": c["text"],
                            }
                            for i, c in enumerate(chunks_data)
                        ])
                        st.dataframe(
                            df_chunks,
                            width='stretch',
                            hide_index=True,
                            column_config={
                                "Text": st.column_config.TextColumn(width="large"),
                                "Retrieved By": st.column_config.TextColumn(width="medium"),
                                "Semantic Rank": st.column_config.TextColumn(width="small"),
                                "BM25 Rank": st.column_config.TextColumn(width="small"),
                                "RRF Score": st.column_config.NumberColumn(format="%.4f"),
                            },
                        )
                    else:
                        st.caption("No chunks retrieved.")

                    st.divider()

                    # For price_details: show per-page LLM calls
                    if is_price:
                        for call in page_calls:
                            st.markdown(f"**Page {call['page']} — LLM Call**")
                            pcol1, pcol2 = st.columns(2)
                            pcol1.metric("Input Tokens", call["input_tokens"])
                            pcol2.metric("Output Tokens", call["output_tokens"])
                            st.text_area(
                                f"Prompt (Page {call['page']})",
                                value=call.get("prompt", ""),
                                height=220,
                                disabled=True,
                                key=f"prompt_{attr}_pg{call['page']}",
                            )
                            st.text_area(
                                f"LLM Output (Page {call['page']})",
                                value=call.get("prompt_output", ""),
                                height=150,
                                disabled=True,
                                key=f"output_{attr}_pg{call['page']}",
                            )
                            st.divider()

                        if canon_call:
                            st.markdown("**Column Canonicalization — LLM Call**")
                            cc1, cc2 = st.columns(2)
                            cc1.metric("Input Tokens", canon_call.get("input_tokens", 0))
                            cc2.metric("Output Tokens", canon_call.get("output_tokens", 0))
                            mapping = canon_call.get("mapping", {})
                            if mapping:
                                df_map = pd.DataFrame(
                                    [{"Original Column": k, "Canonical Column": v}
                                     for k, v in mapping.items()
                                     if k != v],
                                )
                                if not df_map.empty:
                                    st.markdown("Columns renamed during canonicalization:")
                                    st.dataframe(df_map, width='stretch', hide_index=True)
                                else:
                                    st.caption("All column names were already consistent — no renames needed.")
                            st.text_area(
                                "Prompt (Canonicalization)",
                                value=canon_call.get("prompt", ""),
                                height=220,
                                disabled=True,
                                key=f"canon_prompt_{attr}",
                            )
                            st.text_area(
                                "LLM Output (Canonicalization)",
                                value=canon_call.get("prompt_output", ""),
                                height=150,
                                disabled=True,
                                key=f"canon_output_{attr}",
                            )
                            st.divider()
                    else:
                        # Single LLM call
                        st.text_area(
                            "Prompt",
                            value=entry.get("prompt", ""),
                            height=260,
                            disabled=True,
                            key=f"prompt_{attr}",
                        )
                        st.text_area(
                            "LLM Output",
                            value=entry.get("prompt_output", ""),
                            height=150,
                            disabled=True,
                            key=f"output_{attr}",
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
    st.markdown(
        """
        <div class="hero-card">
            <h3>🚀 How it works</h3>
            <span class="hero-step">1️⃣ Upload a contract</span>
            <span class="hero-step">2️⃣ OCR extracts text</span>
            <span class="hero-step">3️⃣ Hybrid RAG indexes chunks</span>
            <span class="hero-step">4️⃣ GPT-4o extracts fields</span>
            <span class="hero-step">5️⃣ Download Excel report</span>
            <br><br>
            <b>Supported:</b> PDF · JPG · PNG · TIFF · XML &nbsp;|&nbsp;
            <b>Extracts:</b> Supplier, Dates, Payment Terms, Rate Card
        </div>
        """,
        unsafe_allow_html=True,
    )
