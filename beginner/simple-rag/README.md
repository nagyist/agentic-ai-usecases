# 📚 RAG Document Chatbot - Streamlit Application

A RAG (Retrieval-Augmented Generation) system that allows users to upload PDF documents and ask questions about their content using OpenAI's GPT models and ChromaDB for vector storage.

![alt text](image.png)

## 🌟 Features

- **PDF Document Processing**: Upload and extract text from PDF files using `pypdf`
- **Intelligent Text Chunking**: Splits documents into 1000-character chunks with 200-character overlap
- **Semantic Search**: Uses OpenAI `text-embedding-3-small` embeddings for accurate context retrieval
- **Smart Message Routing**: Automatically classifies queries as `chitchat`, `overall` (summary), or `rag` (document lookup)
- **Document Summarization**: Generates structured summaries from the first 20 chunks of a document
- **Conversational Interface**: Chat-based interaction with conversation history via Streamlit
- **ChromaDB Vector Store**: In-memory vector storage for fast similarity search (top-k: 4)

## 🏗️ System Architecture & Solution Flow

```mermaid
flowchart TB
    subgraph User["👤 User Interface"]
        A[User Uploads PDF] --> B[Streamlit UI]
        B --> C[User Asks Question]
        D[Display Answer] --> B
    end

    subgraph Processing["⚙️ Document Processing Pipeline"]
        E[PDF File] --> F[pypdf.PdfReader]
        F --> G[Text Extraction]
        G --> H[Text Splitter<br/>Chunk Size: 1000<br/>Overlap: 200]
        H --> I[OpenAI Embeddings<br/>text-embedding-3-small]
        I --> J[Vector Storage<br/>ChromaDB]
    end

    subgraph Routing["🔀 Message Routing"]
        C --> R{Route Classifier<br/>gpt-4o-mini}
        R -->|chitchat| RC[Casual Reply]
        R -->|overall| RS[Document Summary]
        R -->|rag| RQ[RAG Query]
    end

    subgraph Generation["🤖 Response Generation"]
        RQ --> K[Query Embedding]
        K --> L[Similarity Search<br/>Top K: 4]
        L --> M[Context Retrieval]
        M --> N[Prompt + Context]
        N --> O[gpt-4o-mini]
        O --> P[Answer]
        RS --> SL[First 20 Chunks]
        SL --> O
        RC --> O
        P --> D
    end

    subgraph Storage["💾 State Management"]
        S1[(Session State)]
        S2[(Conversation History)]
    end

    B --> E
    J --> L
    B -.-> S1
    C -.-> S2
    D -.-> S2
```

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| UI Framework | Streamlit |
| LLM & Embeddings | OpenAI (`gpt-4o-mini`, `text-embedding-3-small`) |
| PDF Parsing | `pypdf` |
| Vector Database | ChromaDB (in-memory) |
| Environment Config | `python-dotenv` |

## 📦 Installation

```bash
# Clone the repo and navigate to this folder
cd beginner/simple-rag

# Install dependencies
pip install -r requirements.txt
```

## ⚙️ Configuration

Create a `.env` file in this directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

## 🚀 Running the App

```bash
streamlit run app.py
```

## 💬 How to Use

1. Open the app in your browser (default: `http://localhost:8501`)
2. Upload a PDF file using the **sidebar uploader**
3. Click **"🔄 Process Document"** to extract and index the content
4. Type your question in the chat input at the bottom

### Query Types

| Type | Example | Behavior |
|---|---|---|
| Chitchat | "Hi!", "Thanks!" | Friendly reply, reminds you to upload a PDF |
| Summary | "Summarize this", "What is this about?" | Generates a structured summary from first 20 chunks |
| RAG | "What does section 3 say?" | Embeds query, retrieves top-4 chunks, answers from context |

## 📁 Project Structure

```
beginner/simple-rag/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── .env                # API keys (not committed)
└── README.md
```
