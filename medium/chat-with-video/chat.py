"""
chat.py — LLM-routed chat with inline timestamp citations.

Router:  one fast GPT call → "global" | "rag"
Global:  full transcript passed as context (up to 80k tokens)
RAG:     hybrid retrieval (BM25 keyword + vector semantic) with RRF fusion,
         LLM cites 1-2 timestamps inline in answer
"""

from openai import OpenAI
from embedder import search_index
from keyword_index import build_keyword_index
from retrieval_fusion import fuse_and_get_top_k
from transcript import format_timestamp, make_youtube_link
import faiss
import json

MODEL = "gpt-4o-mini"
MAX_FULL_TRANSCRIPT_WORDS = 60_000


# ── System prompts ─────────────────────────────────────────────────────────────

ROUTER_PROMPT = """You are a query classifier for a YouTube video Q&A assistant.

Classify the user's question as one of two types:

"global"  — The question requires understanding the ENTIRE video.
            Examples: summarize, overview, main topics, key takeaways, 
            chapters, structure, what is this video about, full recap.

"rag"     — The question is about a SPECIFIC fact, moment, person, concept, 
            or timestamp in the video. Examples: when did X happen, 
            what did the speaker say about Y, explain concept Z.

Reply with ONLY a JSON object: {"route": "global"} or {"route": "rag"}
No explanation. No other text."""


GLOBAL_SYSTEM_PROMPT = """You are an intelligent video assistant. You have been given the COMPLETE transcript of a YouTube video with timestamps.

Instructions:
- Answer the user's question using the full transcript comprehensively.
- For summaries: cover ALL major sections, not just the beginning.
- For "main sections/topics": identify distinct topic shifts and list each with its start timestamp.
- Cite timestamps inline using this EXACT markdown format: [MM:SS](https://www.youtube.com/watch?v={video_id}&t=Xs)
  where X is the timestamp in seconds. Always include the 's' suffix after the number. Example: &t=315s not &t=315
- Be well-structured — use numbered lists or clear sections.
- Only cite timestamps that are genuinely relevant to that point.
"""

SPECIFIC_SYSTEM_PROMPT = """You are an intelligent video assistant. You have been given relevant excerpts from a YouTube video transcript.

Instructions:
- Answer the question based ONLY on the provided transcript excerpts.
- Cite 1 to 3 timestamps INLINE in your answer using this EXACT markdown format:
  [MM:SS](https://www.youtube.com/watch?v={video_id}&t=Xs)
  where X is the timestamp in seconds. Always include the 's' suffix. Example: &t=315s not &t=315
- Only cite a timestamp when it directly supports the specific sentence you are writing.
- Do NOT list all timestamps at the end — weave them naturally into the answer.
- If the answer spans multiple parts of the video, show each part as a numbered point with its own inline timestamp.
- If the context does not contain the answer, say: "I couldn't find information about that in this video."
- Never make up information not present in the provided context.
"""


# ── LLM Router ────────────────────────────────────────────────────────────────

def classify_query(user_message: str, client: OpenAI) -> str:
    """
    Ask GPT-4o-mini to classify the query as 'global' or 'rag'.
    Falls back to 'rag' on any error.
    """
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": ROUTER_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
            max_tokens=20,
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        route = parsed.get("route", "rag")
        return route if route in ("global", "rag") else "rag"
    except Exception:
        return "rag"  # safe default


# ── Context builders ──────────────────────────────────────────────────────────

def build_full_transcript_context(all_chunks: list[dict]) -> str:
    """Concatenate ALL chunks sorted by time, capped at MAX_FULL_TRANSCRIPT_WORDS."""
    sorted_chunks = sorted(all_chunks, key=lambda c: c["start_time"])
    parts = []
    words_so_far = 0
    for chunk in sorted_chunks:
        chunk_words = len(chunk["text"].split())
        if words_so_far + chunk_words > MAX_FULL_TRANSCRIPT_WORDS:
            parts.append("[... transcript truncated for length ...]")
            break
        ts = format_timestamp(chunk["start_time"])
        parts.append(f"[{ts}] {chunk['text']}")
        words_so_far += chunk_words
    return "\n".join(parts)


def build_rag_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a timestamped context block."""
    parts = []
    for chunk in chunks:
        ts = format_timestamp(chunk["start_time"])
        end_ts = format_timestamp(chunk["end_time"])
        parts.append(f"[{ts} - {end_ts}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


# ── Source extractor (parses inline links from LLM reply) ────────────────────

def extract_sources_from_reply(reply: str, video_id: str) -> list[dict]:
    """
    Parse timestamp markdown links that the LLM wrote inline.
    Matches patterns like [4:32](https://...&t=272s)
    Returns deduplicated list of {timestamp, seconds, link}.
    """
    import re
    # Match [MM:SS] or [H:MM:SS] followed by a YouTube URL with &t=Xs
    # s suffix is optional — LLM sometimes writes &t=315 not &t=315s
    pattern = r'\[([\d]{1,2}:\d{2}(?::\d{2})?)\]\((https://www\.youtube\.com/watch\?v=[\w-]+&t=(\d+)s?)\)'
    matches = re.findall(pattern, reply)
    seen = set()
    sources = []
    for ts_label, url, seconds_str in matches:
        seconds = int(seconds_str)
        if seconds not in seen:
            seen.add(seconds)
            sources.append({
                "timestamp": ts_label,
                "seconds": float(seconds),
                "link": url,
            })
    return sources


# ── Main chat function ────────────────────────────────────────────────────────

def chat_with_video(
    user_message: str,
    conversation_history: list[dict],
    index: faiss.Index,
    chunks: list[dict],
    video_id: str,
    client: OpenAI,
    top_k: int = 5,
    keyword_index=None,
) -> tuple[str, list[dict]]:
    """
    1. Classify query → global | rag
    2. Build context accordingly
    3. For 'rag': use hybrid retrieval (BM25 + semantic with RRF fusion)
    4. Call GPT-4o-mini with inline-timestamp instructions
    5. Parse timestamps from reply for UI chips
    
    Args:
        user_message: User's query
        conversation_history: Previous messages in conversation
        index: FAISS vector index
        chunks: All transcript chunks
        video_id: YouTube video ID
        client: OpenAI client
        top_k: Number of results to return after fusion
        keyword_index: KeywordIndex instance for BM25 search (optional)
        
    Returns:
        Tuple of (reply_text, sources)
    """

    # ── Step 1: Route ──────────────────────────────────────────────────────
    route = classify_query(user_message, client)

    # ── Step 2: Build context ──────────────────────────────────────────────
    if route == "global":
        context = build_full_transcript_context(chunks)
        system_prompt = GLOBAL_SYSTEM_PROMPT.replace("{video_id}", video_id)
        context_label = "FULL VIDEO TRANSCRIPT (with timestamps):"
        max_tokens = 1800
    else:
        # ── Hybrid retrieval: BM25 keyword + semantic vector with RRF fusion ──
        # Retrieve top 10 from each method, then fuse to top_k
        vector_results = search_index(user_message, index, chunks, client, top_k=10)
        
        if keyword_index is not None:
            keyword_results = keyword_index.search(user_message, top_k=10)
            # Fuse using Reciprocal Rank Fusion
            retrieved = fuse_and_get_top_k(
                keyword_results,
                vector_results,
                top_k=top_k,
                rrf_k=60
            )
        else:
            # Fallback: use vector search only if keyword index not available
            retrieved = vector_results[:top_k]
        
        context = build_rag_context(retrieved)
        system_prompt = SPECIFIC_SYSTEM_PROMPT.replace("{video_id}", video_id)
        context_label = "RELEVANT TRANSCRIPT EXCERPTS (hybrid keyword + semantic search):"
        max_tokens = 900

    # ── Step 3: Call LLM ───────────────────────────────────────────────────
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"{context_label}\n\n{context}"},
    ]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
        max_tokens=max_tokens,
    )
    reply = response.choices[0].message.content

    # ── Step 4: Extract inline timestamp links as UI chips ─────────────────
    sources = extract_sources_from_reply(reply, video_id)

    return reply, sources