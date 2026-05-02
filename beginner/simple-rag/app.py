import streamlit as st
import os
import tempfile
from dotenv import load_dotenv
import pypdf
import chromadb
from openai import OpenAI

load_dotenv()

st.set_page_config(
    page_title="RAG Document Chatbot",
    page_icon="📚",
    layout="wide"
)

st.markdown("""
<style>
    .stButton > button { width: 100%; }
</style>
""", unsafe_allow_html=True)

if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'collection' not in st.session_state:
    st.session_state.collection = None
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'chunk_count' not in st.session_state:
    st.session_state.chunk_count = 0


def chunk_text(text, chunk_size=1000, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def extract_pdf_text(pdf_path):
    reader = pypdf.PdfReader(pdf_path)
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


@st.cache_resource
def get_clients():
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    chroma_client = chromadb.Client()
    return openai_client, chroma_client


def get_embedding(client, text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def process_pdf(pdf_path, openai_client, chroma_client):
    try:
        print(f"\n[PROCESS] Extracting text from PDF: {pdf_path}")
        text = extract_pdf_text(pdf_path)
        print(f"[PROCESS] Extracted {len(text)} characters")

        chunks = chunk_text(text)
        print(f"[PROCESS] Split into {len(chunks)} chunks (size=1000, overlap=200)")

        collection_name = "rag_docs"
        try:
            chroma_client.delete_collection(collection_name)
            print("[PROCESS] Deleted existing ChromaDB collection")
        except Exception:
            pass
        collection = chroma_client.create_collection(collection_name)
        print("[PROCESS] Created new ChromaDB collection")

        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            print(f"[PROCESS] Embedding batch {i // batch_size + 1} ({len(batch)} chunks)...")
            embeddings = [get_embedding(openai_client, c) for c in batch]
            ids = [f"chunk_{i + j}" for j in range(len(batch))]
            collection.add(embeddings=embeddings, documents=batch, ids=ids)

        print(f"[PROCESS] Done. {len(chunks)} chunks stored in ChromaDB.")
        return collection, len(chunks)
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None, 0


def route_message(message, openai_client):
    print(f"\n[ROUTER] Input message: {message!r}")
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a routing assistant. Classify the user message into one of three categories:\n"
                    "- 'chitchat': greetings, small talk, compliments, farewells, or anything unrelated to a document (e.g. 'Hi', 'How are you?', 'Thanks', 'Bye').\n"
                    "- 'overall': requests for a summary, overview, or general description of the entire document (e.g. 'summarize', 'what is this document about', 'give me an overview', 'tldr').\n"
                    "- 'rag': specific questions or requests that require looking up particular information from a document.\n"
                    "Reply with ONLY one word: chitchat, overall, or rag."
                )
            },
            {"role": "user", "content": message}
        ]
    )
    route = response.choices[0].message.content.strip().lower()
    route = route if route in ("chitchat", "overall", "rag") else "rag"
    print(f"[ROUTER] Decision: {route}")
    return route


def handle_chitchat(message, openai_client):
    print(f"\n[CHITCHAT] Handling casual message: {message!r}")
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a friendly assistant embedded in a PDF chatbot. "
                    "Respond naturally to casual conversation. "
                    "Keep replies short and friendly, and gently remind the user "
                    "they can upload a PDF and ask questions about it."
                )
            },
            {"role": "user", "content": message}
        ]
    )
    reply = response.choices[0].message.content
    print(f"[CHITCHAT] Response: {reply!r}")
    return reply


def summarize_document(collection, openai_client):
    print("\n[SUMMARY] Fetching first 20 chunks for document summary...")
    result = collection.get(limit=20, include=["documents"])
    chunks = result["documents"]
    print(f"[SUMMARY] Retrieved {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"[SUMMARY] Chunk {i + 1} ({len(chunk)} chars): {chunk[:80].replace(chr(10), ' ')!r}...")

    context = "\n\n".join(chunks)
    print(f"[SUMMARY] Total context length: {len(context)} chars")
    print("[SUMMARY] Calling LLM for summary...")

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Using the document excerpts provided, "
                    "write a clear and concise summary of the document. "
                    "Cover the main topics, key points, and overall purpose. "
                    "Structure the summary with a brief intro, key highlights as bullet points, "
                    "and a one-sentence conclusion."
                )
            },
            {
                "role": "user",
                "content": f"Document excerpts (first 20 chunks):\n\n{context}\n\nPlease summarize this document."
            }
        ]
    )
    summary = response.choices[0].message.content
    print(f"[SUMMARY] Summary generated ({len(summary)} chars)")
    return summary


def ask_question(question, collection, openai_client):
    print(f"\n[RAG] Question: {question!r}")
    print("[RAG] Generating query embedding...")
    query_embedding = get_embedding(openai_client, question)
    print("[RAG] Querying ChromaDB for top 4 relevant chunks...")
    results = collection.query(query_embeddings=[query_embedding], n_results=4)
    retrieved_chunks = results["documents"][0]
    print(f"[RAG] Retrieved {len(retrieved_chunks)} chunks:")
    for i, chunk in enumerate(retrieved_chunks):
        print(f"[RAG]   Chunk {i + 1} ({len(chunk)} chars): {chunk[:80].replace(chr(10), ' ')!r}...")
    context = "\n\n".join(retrieved_chunks)
    print(f"[RAG] Total context length: {len(context)} chars")
    print("[RAG] Calling LLM for answer...")

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that answers questions based on the provided documents. "
                    "If you cannot find the answer in the context, say "
                    "'I cannot find this information in the provided documents.'"
                )
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}"
            }
        ]
    )
    answer = response.choices[0].message.content
    print(f"[RAG] Answer: {answer!r}")
    return answer


def main():
    st.title("📚 RAG Document Chatbot")
    st.markdown("Upload a PDF document and ask questions about its content!")

    openai_client, chroma_client = get_clients()

    with st.sidebar:
        st.header("📄 Document Upload")

        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type="pdf",
            help="Upload a PDF document to chat with its content"
        )

        if uploaded_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            if st.button("🔄 Process Document", type="primary"):
                with st.spinner("Processing PDF..."):
                    collection, chunk_count = process_pdf(tmp_file_path, openai_client, chroma_client)
                    if collection:
                        st.session_state.collection = collection
                        st.session_state.processing_complete = True
                        st.session_state.chunk_count = chunk_count
                        st.success("✅ Document processed! You can now ask questions.")
                    else:
                        st.error("Failed to process document. Please try again.")

                try:
                    os.unlink(tmp_file_path)
                except Exception:
                    pass

        if st.session_state.processing_complete:
            st.info("📊 Status: Document ready for questions")
            st.info(f"🧩 Chunks created: {st.session_state.chunk_count}")
        elif uploaded_file is None:
            st.warning("⚠️ No document loaded. Please upload and process a PDF.")

        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

    col1, col2 = st.columns([0.7, 0.3])

    with col1:
        st.header("💬 Chat Interface")
        st.markdown("""
        **How to use:**
        1. Upload a PDF document using the sidebar
        2. Click "Process Document" to index the content
        3. Ask questions about the document in the chat
        4. The AI will answer based on the document content

        **Features:**
        - 📄 PDF text extraction
        - 🔍 Semantic search
        - 💬 Conversational interface

        **Note:** Uses OpenAI API for embeddings and completions.
        """)

        if st.session_state.processing_complete:
            st.success("✅ System ready!")
        else:
            st.error("❌ No document loaded")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # with col2:
    #     st.header("ℹ️ Information")
        

    if prompt := st.chat_input("Ask a question about your document..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                route = route_message(prompt, openai_client)
                if route == "chitchat":
                    response = handle_chitchat(prompt, openai_client)
                    st.markdown(response)
                elif route == "overall":
                    if st.session_state.processing_complete:
                        response = summarize_document(st.session_state.collection, openai_client)
                        st.markdown(response)
                    else:
                        response = "Please upload and process a PDF document first!"
                        st.error(response)
                elif st.session_state.processing_complete:
                    response = ask_question(prompt, st.session_state.collection, openai_client)
                    st.markdown(response)
                else:
                    response = "Please upload and process a PDF document first!"
                    st.error(response)
        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ OpenAI API key not found! Please set OPENAI_API_KEY in the .env file.")
        st.stop()

    main()
