# 🎬 YT Chat — AI-Powered YouTube Video Assistant

Chat with any YouTube video. Answers are grounded in the transcript with clickable timestamp links.

## Features

- **Multi-video support** — Load and switch between multiple videos
- **Thumbnail & metadata preview** — See video info at a glance
- **Grounded answers** — AI only answers from the actual transcript
- **Timestamp citations** — Every answer links to exact moments in the video
- **Topic navigation** — Find every timestamp where a topic is discussed
- **Semantic search** — FAISS + OpenAI embeddings for accurate retrieval

## Setup

### 1. Prerequisites
- Python 3.10+
- An OpenAI API key (get one at https://platform.openai.com)

### 2. Install dependencies

```bash
cd yt-chat
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

- Load multiple videos — they stay in the sidebar for quick switching
- Ask "where does X get explained?" for timestamp navigation
- Answers with 🔵 source chips = clickable timestamps to jump in the video
- Works best with videos that have auto-generated or manual captions

## Stack

| Component | Tool |
|---|---|
| LLM | GPT-4o mini |
| Embeddings | text-embedding-3-small |
| Vector store | FAISS (local) |
| Transcripts | youtube-transcript-api |
| Frontend | Streamlit |
