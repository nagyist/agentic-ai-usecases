# 🎬 YT Chat — AI-Powered YouTube Video Assistant

Agentic AI Project: Chat with any YouTube video. Answers are grounded in the transcript with clickable timestamp links.

Here is the complete end to end [medium article](https://medium.com/@alphaiterations/stop-watching-youtube-videos-start-chatting-with-them-58b3e5a964b1?postPublishedType=initial)

## Features

- **Thumbnail & metadata preview** — See video info at a glance
- **Grounded answers** — AI only answers from the actual transcript
- **Timestamp citations** — Every answer links to exact moments in the video
- **Topic navigation** — Find every timestamp where a topic is discussed
- **Hybrid retrieval** — BM25 keyword + FAISS semantic search fused with RRF
- **Smart query routing** — Automatically chooses global summary vs focused RAG answers

## Retrieval Pipeline

1. Transcript is chunked with timestamps
2. Semantic index is built using OpenAI embeddings + FAISS
3. Keyword index is built using BM25
4. Top results from both methods are fused using Reciprocal Rank Fusion (RRF)
5. Assistant answers with inline timestamp citations

## Setup

### 1. Prerequisites
- Python 3.10+
- An OpenAI API key (get one at https://platform.openai.com)

### 2. Install dependencies

```bash
cd agentic-ai-usecases/medium/chat-with-video
pip install -r requirements.txt
```

### 3. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`

## Usage

1. Enter your **OpenAI API key** in the sidebar
2. Paste a **YouTube URL** and click **Load & Index Video**
3. Wait for the transcript to be fetched and indexed (~10–30 seconds)
4. **Chat tab** — Ask anything about the video
5. **Navigate Timestamps tab** — Search for any topic to find where it's discussed

## Tips

- Ask "where does X get explained?" for timestamp navigation
- Answers with 🔵 source chips = clickable timestamps to jump in the video
- Works best with videos that have auto-generated or manual captions

## Stack

| Component | Tool |
|---|---|
| LLM | GPT-4o mini |
| Embeddings | text-embedding-3-small |
| Vector store | FAISS (local) |
| Keyword retrieval | BM25 (rank-bm25) |
| Fusion | Reciprocal Rank Fusion (RRF) |
| Transcripts | youtube-transcript-api |
| Frontend | Streamlit |
