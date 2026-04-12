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
from chat import chat_with_video

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="YT Chat",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600&family=Roboto:wght@300;400;500&display=swap');

/* Reset & base */
html, body, [class*="css"] {
    font-family: 'Roboto', sans-serif;
    margin: 0; padding: 0;
}

.stApp {
    background: #0f0f0f;
    color: #f1f1f1;
}

/* Hide streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebar"] { display: none; }
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── TOP NAV BAR ── */
.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #0f0f0f;
    border-bottom: 1px solid #272727;
    padding: 10px 20px;
    position: sticky;
    top: 0;
    z-index: 100;
}
.topbar-left {
    display: flex;
    align-items: center;
    gap: 12px;
}
.yt-logo {
    font-size: 1.3rem;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.5px;
}
.yt-logo span { color: #ff0000; }
.url-input-wrap {
    flex: 1;
    max-width: 600px;
    margin: 0 24px;
}

/* ── MAIN TWO-PANEL LAYOUT ── */
.main-panels {
    display: flex;
    height: calc(100vh - 57px);
    overflow: hidden;
}

/* Left: video panel */
.video-panel {
    flex: 1;
    background: #000;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
.video-embed-wrap {
    position: relative;
    width: 100%;
    padding-top: 56.25%; /* 16:9 */
    background: #000;
    flex-shrink: 0;
}
.video-embed-wrap iframe {
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    border: none;
}
.video-info {
    padding: 16px 20px;
    border-top: 1px solid #272727;
    background: #0f0f0f;
    flex-shrink: 0;
}
.video-title {
    font-family: 'Roboto', sans-serif;
    font-size: 1.1rem;
    font-weight: 500;
    color: #f1f1f1;
    margin: 0 0 4px 0;
    line-height: 1.4;
}
.video-channel {
    font-size: 0.82rem;
    color: #aaa;
    margin: 0;
}

/* Right: chat panel */
.chat-panel {
    width: 400px;
    min-width: 340px;
    max-width: 420px;
    background: #212121;
    border-left: 1px solid #272727;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    height: 100%;
}

.chat-header {
    padding: 14px 18px 12px;
    border-bottom: 1px solid #333;
    flex-shrink: 0;
    background: #212121;
}
.chat-header-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 2px;
}
.chat-title {
    font-family: 'Roboto', sans-serif;
    font-size: 1rem;
    font-weight: 500;
    color: #f1f1f1;
    margin: 0;
}
.gemini-star {
    font-size: 1.1rem;
    margin-right: 6px;
}
.chat-subtitle {
    font-size: 0.75rem;
    color: #aaa;
    margin-top: 2px;
}

/* Suggested questions */
.suggestions {
    padding: 14px 16px 8px;
    border-bottom: 1px solid #2d2d2d;
    flex-shrink: 0;
}
.suggestions-label {
    font-size: 0.78rem;
    color: #aaa;
    margin-bottom: 8px;
}
.suggestion-chips {
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.suggestion-chip {
    background: transparent;
    border: 1px solid #3d3d3d;
    border-radius: 18px;
    padding: 7px 14px;
    font-size: 0.8rem;
    color: #c8c8c8;
    cursor: pointer;
    text-align: right;
    width: fit-content;
    align-self: flex-end;
    transition: background 0.15s, border-color 0.15s;
    line-height: 1.3;
}
.suggestion-chip:hover {
    background: #2d2d2d;
    border-color: #555;
    color: #f1f1f1;
}

/* Chat messages area */
.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    scrollbar-width: thin;
    scrollbar-color: #3d3d3d #212121;
}
/* Thinking dots */
@keyframes thinking-pulse {
    0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
    40% { opacity: 1; transform: scale(1.1); }
}
.thinking-dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #666;
    animation: thinking-pulse 1.2s ease-in-out infinite;
}

/* Timestamp dropdown chip — pure CSS, no JS */
.ts-dropdown {
    position: relative;
    display: inline-block;
    vertical-align: middle;
    margin: 0 2px;
}
.ts-chip {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    background: #1e2a3a;
    border: 1px solid #2a3f5a;
    border-radius: 5px;
    padding: 1px 8px;
    font-size: 0.78rem;
    font-family: 'Roboto Mono', monospace;
    color: #8ab4f8;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
    transition: background 0.12s;
}
.ts-chip:hover { background: #253549; color: #b0ccff; }
.ts-menu {
    display: none;
    position: absolute;
    bottom: calc(100% + 4px);
    left: 0;
    background: #1a1f2e;
    border: 1px solid #2d3a50;
    border-radius: 8px;
    min-width: 200px;
    z-index: 9999;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(0,0,0,0.5);
}
.ts-dropdown:hover .ts-menu { display: block; }
.ts-option {
    display: block;
    padding: 9px 14px;
    font-size: 0.8rem;
    color: #c8d4e8;
    text-decoration: none;
    cursor: pointer;
    transition: background 0.12s;
    white-space: nowrap;
}
.ts-option:hover { background: #253549; color: #fff; }
.ts-option + .ts-option { border-top: 1px solid #2d3a50; }
.chat-messages::-webkit-scrollbar { width: 4px; }
.chat-messages::-webkit-scrollbar-track { background: #212121; }
.chat-messages::-webkit-scrollbar-thumb { background: #3d3d3d; border-radius: 2px; }

/* Message bubbles */
.msg-user {
    align-self: flex-end;
    background: #2d2d2d;
    border-radius: 18px 18px 4px 18px;
    padding: 10px 14px;
    max-width: 85%;
    font-size: 0.87rem;
    color: #f1f1f1;
    line-height: 1.5;
    word-wrap: break-word;
}
.msg-ai-wrap {
    align-self: flex-start;
    max-width: 95%;
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.msg-ai-label {
    font-size: 0.72rem;
    color: #888;
    display: flex;
    align-items: center;
    gap: 4px;
    margin-bottom: 2px;
}
.msg-ai {
    background: transparent;
    font-size: 0.87rem;
    color: #e0e0e0;
    line-height: 1.6;
    word-wrap: break-word;
}
.msg-ai a {
    color: #8ab4f8;
    text-decoration: none;
}
.msg-ai a:hover { text-decoration: underline; }

/* Timestamp source chips */
.source-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 4px;
}
.inline-ts {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    background: #1e2a3a;
    border: 1px solid #2a3f5a;
    border-radius: 5px;
    padding: 1px 7px;
    font-size: 0.78rem;
    font-family: 'Roboto Mono', monospace;
    color: #8ab4f8;
    cursor: pointer;
    transition: background 0.12s, transform 0.1s;
    user-select: none;
    white-space: nowrap;
    vertical-align: middle;
    margin: 0 2px;
}
.inline-ts:hover { background: #253549; color: #b0ccff; transform: translateY(-1px); }
.inline-ts:active { transform: translateY(0); background: #2a3f5a; }

/* Chat input area */
.chat-input-area {
    padding: 10px 14px 8px;
    border-top: 1px solid #2d2d2d;
    background: #212121;
    flex-shrink: 0;
}
.chat-disclaimer {
    text-align: center;
    font-size: 0.67rem;
    color: #666;
    padding: 4px 0 0;
}

/* Streamlit input overrides */
.stTextInput > div > div > input {
    background: #2d2d2d !important;
    border: 1px solid #3d3d3d !important;
    border-radius: 22px !important;
    color: #f1f1f1 !important;
    font-size: 0.87rem !important;
    padding: 10px 18px !important;
    font-family: 'Roboto', sans-serif !important;
}
.stTextInput > div > div > input:focus {
    border-color: #555 !important;
    box-shadow: none !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder { color: #888 !important; }

.stButton > button {
    background: transparent;
    border: none;
    color: #8ab4f8;
    font-size: 0.85rem;
    font-weight: 500;
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-family: 'Roboto', sans-serif;
    transition: background 0.15s;
}
.stButton > button:hover { background: #2d2d2d; color: #c0d4ff; }

/* Empty / loading states */
.empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 32px 24px;
    color: #888;
}
.empty-icon { font-size: 2rem; margin-bottom: 10px; }
.empty-text { font-size: 0.85rem; line-height: 1.6; }

/* Top URL bar inputs */
div[data-testid="stHorizontalBlock"] .stTextInput > div > div > input {
    background: #121212 !important;
    border: 1px solid #303030 !important;
    border-radius: 22px !important;
    color: #f1f1f1 !important;
    font-size: 0.88rem !important;
    padding: 9px 16px !important;
}

/* Spinner */
.stSpinner > div { border-top-color: #aaa !important; }

/* Chips (suggestion buttons) styled via st.button with key trick */
div[data-suggestion="true"] .stButton > button {
    background: transparent !important;
    border: 1px solid #3d3d3d !important;
    border-radius: 18px !important;
    color: #c8c8c8 !important;
    font-size: 0.8rem !important;
    padding: 7px 14px !important;
    width: 100% !important;
    text-align: right !important;
    justify-content: flex-end !important;
}
</style>
""", unsafe_allow_html=True)


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
                prog.progress(95, text="Almost done...")
                st.session_state.videos[video_id] = {
                    "meta": meta, "chunks": chunks,
                    "index": index, "chunk_count": len(chunks),
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
        # Render player via components.html so JS runs in its own iframe
        # and can receive postMessage seek commands from sibling chip clicks
        player_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
          * {{ margin:0; padding:0; box-sizing:border-box; }}
          body {{ background:#000; overflow:hidden; }}
          #player-wrap {{
            position: relative;
            width: 100%;
            padding-top: 56.25%;
            background: #000;
          }}
          #yt-player {{
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            border: none;
          }}
          .info {{
            background: #0f0f0f;
            padding: 10px 14px;
            border-top: 1px solid #272727;
          }}
          .title {{
            font-family: Roboto, sans-serif;
            font-size: 0.98rem;
            font-weight: 500;
            color: #f1f1f1;
            margin-bottom: 3px;
            line-height: 1.4;
          }}
          .channel {{
            font-size: 0.78rem;
            color: #aaa;
            margin-bottom: 6px;
          }}
          .meta-row {{
            display: flex;
            align-items: center;
            gap: 12px;
          }}
          .badge {{
            font-size: 0.68rem;
            color: #555;
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 4px;
            padding: 2px 7px;
          }}
          .yt-link {{
            font-size: 0.68rem;
            color: #8ab4f8;
            text-decoration: none;
          }}
        </style>
        </head>
        <body>
          <div id="player-wrap">
            <iframe
              id="yt-player"
              name="yt-player"
              src="https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1&enablejsapi=1&origin=http://localhost"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen>
            </iframe>
          </div>
          <div class="info">
            <div class="title">{meta['title']}</div>
            <div class="channel">{meta['author']}</div>
            <div class="meta-row">
              <span class="badge">{video['chunk_count']} chunks indexed</span>
              <a class="yt-link" href="{meta['url']}" target="_blank">↗ Open on YouTube</a>
            </div>
          </div>

          <script>
            // Relay YT_SEEK from any parent frame down into the YouTube iframe
            function doSeek(data) {{
              if (typeof data === 'string') {{
                try {{ data = JSON.parse(data); }} catch(e) {{ return; }}
              }}
              if (!data || data.type !== 'YT_SEEK') return;
              var player = document.getElementById('yt-player');
              if (!player || !player.contentWindow) return;
              var sec = parseInt(data.seconds);
              player.contentWindow.postMessage(
                JSON.stringify({{ event:'command', func:'seekTo', args:[sec, true] }}), '*'
              );
              player.contentWindow.postMessage(
                JSON.stringify({{ event:'command', func:'playVideo', args:[] }}), '*'
              );
            }}
            window.addEventListener('message', function(e) {{ doSeek(e.data); }});
          </script>
        </body>
        </html>
        """
        components.html(player_html, height=600, scrolling=False)

    # ── RIGHT: Chat panel ──────────────────────────────────────────────────────
    with right_col:
        # Chat header
        st.markdown("""
        <div style="background:#212121;border:1px solid #2d2d2d;border-radius:10px;
                    overflow:hidden;display:flex;flex-direction:column;">
            <div style="padding:14px 18px 10px;border-bottom:1px solid #2d2d2d;">
                <div style="display:flex;align-items:center;gap:6px;">
                    <span style="font-size:1rem;">✦</span>
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

                        # Convert YouTube timestamp links → seekVideo() onclick spans
                        # Matches: [MM:SS](https://www.youtube.com/watch?v=...&t=Xs)
                        def replace_ts_link(m):
                            label   = m.group(1)
                            url     = m.group(2)
                            seconds = m.group(3)
                            yt_url  = f"https://www.youtube.com/watch?v={video_id}&t={seconds}s"
                            embed_url = f"https://www.youtube.com/embed/{video_id}?start={seconds}&autoplay=1&enablejsapi=1"
                            return (
                                '<span class="ts-dropdown">'
                                f'<span class="ts-chip">&#9201; {label}</span>'
                                '<span class="ts-menu">'
                                f'<a class="ts-option" href="{yt_url}" target="_blank">&#8599; Open in new tab</a>'
                                f'<a class="ts-option" href="{embed_url}" target="yt-player">&#9654; Jump in video panel</a>'
                                '</span>'
                                '</span>'
                            )


                        # s suffix is optional — LLM sometimes writes &t=315 not &t=315s
                        ts_pattern = (
                            r'\[([\d]{1,2}:[\d]{2}(?::[\d]{2})?)\]'
                            r'\((https://www\.youtube\.com/watch\?v=[\w-]+&t=(\d+)s?)\)'
                        )
                        reply_html = _re.sub(ts_pattern, replace_ts_link, reply_raw)

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
                        reply_html = reply_html.replace('\n', '<br>')

                        st.markdown(f"""
                        <div style="margin:6px 0;">
                            <div style="font-size:0.7rem;color:#777;margin-bottom:4px;
                                        display:flex;align-items:center;gap:4px;">
                                <span>✦</span> AI Assistant
                            </div>
                            <div style="font-size:0.86rem;color:#e0e0e0;line-height:1.6;
                                        word-wrap:break-word;">
                                {reply_html}
                            </div>
                        </div>

                        """, unsafe_allow_html=True)
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
                reply, sources = chat_with_video(
                    question, history_for_api,
                    index, chunks, video_id, get_client(),
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