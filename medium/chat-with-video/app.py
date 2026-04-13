"""
app.py - YouTube AI Chat — Streamlit frontend
Two-panel layout: embedded video left, chat right
"""

import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import time
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

from transcript import extract_video_id, fetch_transcript, chunk_transcript, format_timestamp, make_youtube_link
from metadata import fetch_metadata
from embedder import build_index
from keyword_index import build_keyword_index
from chat import chat_with_video

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="YT Chat",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ── Custom CSS ─────────────────────────────────────────────────────────────────

def load_local_css(filename: str):
    css_path = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"Missing CSS file: {css_path}")

load_local_css("style.css")

# ── Query param handler is already set up above ──────────────────────────────────────


# ── Session state ──────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "videos": {},
        "active_video_id": None,
        "conversations": {},
        "client": None,
        "pending_input": "",
        "awaiting_answer": "",  # question waiting for LLM response
        "processing_answer": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Handle jump-to-timestamp from HTML button click
if "jump_to" in st.query_params:
    try:
        jump_seconds = st.query_params.get("jump_to")
        if jump_seconds:
            st.session_state.jump_to_seconds = int(jump_seconds)
            # Clear the param to avoid re-triggering
            params = dict(st.query_params)
            del params["jump_to"]
            st.query_params.clear()
            for k, v in params.items():
                st.query_params[k] = v
    except Exception as e:
        print(f"Error handling jump_to param: {e}")


def get_client():
    return st.session_state.client


def active_video():
    vid = st.session_state.active_video_id
    if vid and vid in st.session_state.videos:
        return st.session_state.videos[vid]
    return None

def active_conversation():
    vid = st.session_state.active_video_id
    if vid and vid not in st.session_state.conversations:
        st.session_state.conversations[vid] = []
    if vid:
        return st.session_state.conversations[vid]
    return []


# ── TOP NAV ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
  <div style="font-size:1.25rem;font-weight:700;color:#fff;letter-spacing:-0.3px;">
    <span style="color:#ff0000;">▶</span> YT Chat
  </div>
</div>
""", unsafe_allow_html=True)

# Controls row below topbar
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([4, 1, 1])
with ctrl_col1:
    yt_url = st.text_input(
        "url", placeholder="Paste YouTube URL...",
        label_visibility="collapsed", key="url_input"
    )
with ctrl_col2:
    load_btn = st.button("Load Video", use_container_width=True)
with ctrl_col3:
    # Show loaded videos selector if multiple
    if len(st.session_state.videos) > 1:
        video_options = {v["meta"]["title"][:28] + "…": k
                        for k, v in st.session_state.videos.items()}
        selected_label = st.selectbox(
            "Switch", list(video_options.keys()),
            label_visibility="collapsed"
        )
        st.session_state.active_video_id = video_options[selected_label]
    elif len(st.session_state.videos) == 1:
        st.markdown(
            f'<div style="font-size:0.75rem;color:#888;padding:8px 0;">1 video loaded</div>',
            unsafe_allow_html=True
        )

# Handle load
if load_btn:
    url_val = yt_url.strip()

    if not OPENAI_API_KEY:
        st.error("OPENAI_API_KEY not found in .env file.")
        st.stop()
    elif not url_val:
        st.error("Paste a YouTube URL.")
    else:
        if not st.session_state.client:
            st.session_state.client = OpenAI(api_key=OPENAI_API_KEY)

        video_id = extract_video_id(url_val)
        if not video_id:
            st.error("Couldn't parse a video ID from that URL.")
        elif video_id in st.session_state.videos:
            st.session_state.active_video_id = video_id
            st.success("Already loaded — switched to it.")
            st.rerun()
        else:
            prog = st.progress(0, text="Fetching metadata...")
            try:
                meta = fetch_metadata(video_id)
                prog.progress(15, text="Fetching transcript...")
                raw = fetch_transcript(video_id)
                prog.progress(40, text="Chunking transcript...")
                chunks = chunk_transcript(raw)
                prog.progress(60, text=f"Embedding {len(chunks)} chunks...")
                index, chunks = build_index(chunks, get_client())
                prog.progress(80, text="Building keyword index...")
                keyword_index = build_keyword_index(chunks)
                prog.progress(95, text="Almost done...")
                st.session_state.videos[video_id] = {
                    "meta": meta, "chunks": chunks,
                    "index": index, "keyword_index": keyword_index,
                    "chunk_count": len(chunks),
                }
                st.session_state.active_video_id = video_id
                st.session_state.conversations[video_id] = []
                prog.progress(100, text="Ready!")
                time.sleep(0.3)
                prog.empty()
                st.rerun()
            except ValueError as e:
                prog.empty()
                st.error(str(e))
            except Exception as e:
                prog.empty()
                st.error(f"Error: {e}")

st.markdown("<div style='height:1px;background:#272727;margin:0;'></div>", unsafe_allow_html=True)

# ── MAIN TWO-PANEL LAYOUT ──────────────────────────────────────────────────────
video = active_video()

if not video:
    # Empty state
    st.markdown("""
    <div style="display:flex;align-items:center;justify-content:center;
                height:calc(100vh - 120px);flex-direction:column;
                text-align:center;color:#555;gap:12px;">
        <div style="font-size:3rem;">▶</div>
        <div style="font-size:1rem;color:#888;font-weight:500;">Paste a YouTube URL above to get started</div>
        <div style="font-size:0.82rem;color:#555;max-width:380px;line-height:1.6;">
            Chat with any video — answers grounded in the transcript with clickable timestamps
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    meta = video["meta"]
    chunks = video["chunks"]
    index = video["index"]
    video_id = meta["video_id"]
    conversation = active_conversation()

    # ── Two columns: video | chat ──────────────────────────────────────────────
    left_col, right_col = st.columns([1.15, 0.85], gap="small")

    # ── LEFT: Video embed + info ───────────────────────────────────────────────
    with left_col:
        origin = "http://localhost:8501"
        
        # Create placeholder for video panel to allow re-rendering on jump
        video_placeholder = st.empty()
        
        # Check if we need to update start time
        start_time = 0
        if hasattr(st.session_state, 'jump_to_seconds') and st.session_state.jump_to_seconds:
            start_time = st.session_state.jump_to_seconds
            st.session_state.jump_to_seconds = None  # Reset for next jump
        
        with video_placeholder.container():
            st.markdown(f"""
            <div class="video-panel">
                <div class="video-embed-wrap">
                    <iframe
                        id="yt-player"
                        name="yt-player"
                        src="https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1&enablejsapi=1&autoplay=1&start={start_time}&origin={origin}"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                        allowfullscreen>
                    </iframe>
                </div>
                <div class="video-info">
                    <div class="video-title">{meta['title']}</div>
                    <div class="video-channel">{meta['author']}</div>
                    <div class="meta-row" style="display:flex;align-items:center;gap:12px;">
                        <span class="badge">{video['chunk_count']} chunks indexed</span>
                        <a class="yt-link" href="{meta['url']}" target="_blank">↗ Open on YouTube</a>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)


    # ── RIGHT: Chat panel ──────────────────────────────────────────────────────
    with right_col:
        # Chat header
        st.markdown("""
        <div style="background:#212121;border:1px solid #2d2d2d;border-radius:10px;
                    overflow:hidden;display:flex;flex-direction:column;">
            <div style="padding:14px 18px 10px;border-bottom:1px solid #2d2d2d;">
                <div style="display:flex;align-items:center;gap:6px;">
                    <span style="font-size:1rem;">💬</span>
                    <span style="font-size:0.95rem;font-weight:500;color:#f1f1f1;">Ask about this video</span>
                </div>
                <div style="font-size:0.73rem;color:#777;margin-top:2px;">
                    Answers grounded in transcript · click timestamps to jump
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Suggested questions + chat container
        # Height shrinks when suggestions are visible so input stays on screen
        suggestions = [
            "Summarize this video",
            "What are the main topics discussed?",
            "What are the key takeaways?",
        ]

        if st.session_state.get("processing_answer"):
            st.markdown(
                "<style>div[data-suggestion='true']{display:none !important;}</style>",
                unsafe_allow_html=True
            )

        if not conversation:
            is_thinking = bool(st.session_state.get("processing_answer"))
            chat_container = st.container(height=230)
            with chat_container:
                if is_thinking:
                    question_text = st.session_state.get("awaiting_answer", "")
                    st.markdown(f"""
                    <div style="display:flex;justify-content:flex-end;margin:6px 0;">
                        <div style="background:#2d2d2d;border-radius:18px 18px 4px 18px;
                                    padding:10px 14px;max-width:88%;font-size:0.86rem;
                                    color:#f1f1f1;line-height:1.5;word-wrap:break-word;">
                            {question_text}
                        </div>
                    </div>
                    <div style="padding:8px 4px;">
                        <div style="font-size:0.7rem;color:#777;margin-bottom:6px;">✦ AI Assistant</div>
                        <div style="display:flex;align-items:center;gap:6px;">
                            <span class="thinking-dot"></span>
                            <span class="thinking-dot" style="animation-delay:.2s"></span>
                            <span class="thinking-dot" style="animation-delay:.4s"></span>
                            <span style="margin-left:4px;font-size:0.8rem;color:#555;">Thinking...</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown('<div data-suggestion="true">', unsafe_allow_html=True)
                    st.markdown("""
                    <div style="font-size:0.76rem;color:#888;margin-bottom:8px;padding:2px 2px 0;">
                        Not sure what to ask? Choose something:
                    </div>
                    """, unsafe_allow_html=True)
                    for i, s in enumerate(suggestions):
                        if st.button(s, key=f"suggestion_{i}", use_container_width=True):
                            st.session_state.pending_input = s
                            st.rerun()
                    st.markdown("""
                    <div style="text-align:center;color:#444;font-size:0.8rem;
                                padding:14px 16px 4px;line-height:1.7;">
                        Hello! Curious about what you're watching?<br>I'm here to help.
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
        else:
            # Conversation active — full height container, no suggestions
            chat_container = st.container(height=420)
            with chat_container:
                for turn in conversation:
                    if turn["role"] == "user":
                        st.markdown(f"""
                        <div style="display:flex;justify-content:flex-end;margin:6px 0;">
                            <div style="background:#2d2d2d;border-radius:18px 18px 4px 18px;
                                        padding:10px 14px;max-width:88%;font-size:0.86rem;
                                        color:#f1f1f1;line-height:1.5;word-wrap:break-word;">
                                {turn['content']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        import re as _re

                        reply_raw = turn["content"]

                        # Extract timestamps before processing display text
                        ts_pattern = r'\[([\d]{1,2}:[\d]{2}(?::[\d]{2})?)\]\((https://www\.youtube\.com/watch\?v=[\w-]+&t=(\d+)s?)\)'
                        timestamps = list(_re.finditer(ts_pattern, reply_raw))

                        # Remove timestamp links from display text, leave just the content
                        reply_html = _re.sub(ts_pattern, r'\1', reply_raw)

                        # Markdown formatting
                        reply_html = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', reply_html)
                        # Numbered lists: lines starting with "1) " or "1. "
                        reply_html = _re.sub(
                            r'(?m)^(\d+)[.)]\ ',
                            lambda mm: f'<br><strong>{mm.group(1)}.</strong> ',
                            reply_html
                        )
                        # Bullet lists
                        reply_html = _re.sub(r'(?m)^[-•]\ ', '<br>• ', reply_html)
                        # Split response into paragraphs and process each separately
                        paragraphs = reply_raw.split('\n\n')
                        
                        st.markdown("<div style='margin:6px 0;'><div style='font-size:0.7rem;color:#777;margin-bottom:4px;display:flex;align-items:center;gap:4px;'><span>✦</span> AI Assistant</div></div>", unsafe_allow_html=True)
                        
                        for para_idx, para in enumerate(paragraphs):
                            if not para.strip():
                                continue
                            
                            para_timestamps = list(_re.finditer(ts_pattern, para))
                            
                            if not para_timestamps:
                                # No timestamps in this paragraph, just render normally
                                para_html = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', para)
                                para_html = _re.sub(r'(?m)^(\d+)[.)] ', lambda mm: f'<strong>{mm.group(1)}.</strong> ', para_html)
                                para_html = _re.sub(r'(?m)^[-•] ', '• ', para_html)
                                para_html = para_html.replace('\n', '<br>')
                                st.markdown(f'<div style="font-size:0.86rem;color:#e0e0e0;line-height:1.6;word-wrap:break-word;margin-bottom:8px;">{para_html}</div>', unsafe_allow_html=True)
                            else:
                                # Render paragraph text with formatting, removing timestamp markdown links
                                para_display = para
                                # Remove timestamp links [MM:SS](url) -> just keep the text before
                                para_display = _re.sub(ts_pattern, '', para_display)
                                para_display = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', para_display)
                                para_display = _re.sub(r'(?m)^(\d+)[.)] ', lambda mm: f'<strong>{mm.group(1)}.</strong> ', para_display)
                                para_display = _re.sub(r'(?m)^[-•] ', '• ', para_display)
                                para_display = para_display.replace('\n', '<br>')
                                
                                st.markdown(f'<div style="font-size:0.86rem;color:#e0e0e0;line-height:1.6;margin-bottom:6px;">{para_display}</div>', unsafe_allow_html=True)
                                
                                # Render timestamp buttons in a row below text
                                if para_timestamps:
                                    button_cols = st.columns(len(para_timestamps), gap='small')
                                    for idx, match in enumerate(para_timestamps):
                                        label = match.group(1)
                                        seconds = match.group(3)
                                        with button_cols[idx]:
                                            if st.button(f'⏱ {label}', key=f'ts_btn_{video_id}_{para_idx}_{label}_{seconds}', use_container_width=True):
                                                st.session_state.jump_to_seconds = int(seconds)
                                                st.rerun()
                # Show thinking bubble inside container if answer is pending
                if st.session_state.get("processing_answer"):
                    st.markdown("""
                    <div style="margin:6px 0;">
                        <div style="font-size:0.7rem;color:#777;margin-bottom:4px;
                                    display:flex;align-items:center;gap:4px;">
                            <span>✦</span> AI Assistant
                        </div>
                        <div style="display:flex;align-items:center;gap:6px;
                                    color:#555;font-size:0.82rem;padding:4px 0;">
                            <span class="thinking-dot"></span>
                            <span class="thinking-dot" style="animation-delay:.2s"></span>
                            <span class="thinking-dot" style="animation-delay:.4s"></span>
                            <span style="margin-left:4px;">Thinking...</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # Input row
        inp_col, btn_col = st.columns([5, 1])
        with inp_col:
            user_input = st.text_input(
                "Ask", placeholder="Ask a question...",
                label_visibility="collapsed", key="chat_input"
            )
        with btn_col:
            send_btn = st.button("→", key="send_btn")

        # ── Two-phase send ────────────────────────────────────────────────────
        # Phase 1: user submits → store question, append to convo, rerun immediately
        #          so the question bubble appears before LLM is called.
        # Phase 2: awaiting_answer is set → call LLM, append reply, rerun.

        # Detect new submission
        new_question = ""
        if st.session_state.pending_input:
            new_question = st.session_state.pending_input
            st.session_state.pending_input = ""
        elif send_btn and user_input.strip():
            new_question = user_input.strip()

        if new_question:
            # Phase 1 — show question immediately
            conversation.append({"role": "user", "content": new_question, "sources": []})
            st.session_state.awaiting_answer = new_question
            st.session_state.processing_answer = True
            st.rerun()

        # Phase 2 — question is visible, now generate the answer
        if st.session_state.awaiting_answer and st.session_state.processing_answer:
            question = st.session_state.awaiting_answer

            history_for_api = [
                {"role": t["role"], "content": t["content"]}
                for t in conversation
                if not (t["role"] == "user" and t["content"] == question and t == conversation[-1])
            ]

            try:
                keyword_index = video.get("keyword_index")
                reply, sources = chat_with_video(
                    question, history_for_api,
                    index, chunks, video_id, get_client(),
                    keyword_index=keyword_index,
                )
                conversation.append({"role": "assistant", "content": reply, "sources": sources})
            except Exception as e:
                conversation.append({
                    "role": "assistant",
                    "content": f"Sorry, something went wrong: {e}",
                    "sources": []
                })
            finally:
                st.session_state.awaiting_answer = ""
                st.session_state.processing_answer = False
            st.rerun()

        # Disclaimer
        st.markdown("""
        <div style="text-align:center;font-size:0.67rem;color:#555;padding:4px 0 2px;">
            AI can make mistakes, so double-check it.
        </div>
        """, unsafe_allow_html=True)

        # Clear chat
        if conversation:
            if st.button("Clear chat", key="clear_chat"):
                st.session_state.conversations[video_id] = []
                st.rerun()