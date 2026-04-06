# agent/nodes.py
# ─────────────────────────────────────────────────────────────────────────────
# LangGraph node functions.  Each node receives the full AgentState dict and
# returns a partial dict with only the keys it updates.
# ─────────────────────────────────────────────────────────────────────────────

import mlflow
from openai import OpenAI
from agent.router import route_question
from tools.sql_tool        import run_sql_tool
from tools.rag_tool        import run_rag_tool
from tools.web_search_tool import run_web_search_tool
from config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, OPENAI_API_KEY
from observability import trace, set_attrs  # Import observability utilities

client = OpenAI(api_key=OPENAI_API_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# Node 1 — Router
# ─────────────────────────────────────────────────────────────────────────────

def router_node(state: dict) -> dict:
    """
    Classify the user message and set state["route"].
    """
    routing = route_question(
        user_message=state["user_message"],
        conversation_history=state["conversation_history"],
    )
    print(f"\n[router] → {routing['route'].upper()}  |  {routing['reason']}")
    return {
        "route":        routing["route"],
        "route_reason": routing["reason"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 2a — SQL Tool Node
# ─────────────────────────────────────────────────────────────────────────────

def sql_node(state: dict) -> dict:
    """
    Generate & execute a SQL query, store raw result in state.
    """
    print("[sql_node] Generating and executing SQL …")
    result = run_sql_tool(
        user_question=state["user_message"],
        conversation_history=state["conversation_history"],
    )
    print(f"[sql_node] SQL: {result['sql']}")
    if result["error"]:
        print(f"[sql_node] ERROR: {result['error']}")
    else:
        print(f"[sql_node] {len(result['rows'])} rows returned.")
    return {"sql_result": result}


# ─────────────────────────────────────────────────────────────────────────────
# Node 2b — RAG Tool Node
# ─────────────────────────────────────────────────────────────────────────────

def rag_node(state: dict) -> dict:
    """
    Retrieve relevant PDF chunks and synthesise an answer.
    """
    print("[rag_node] Retrieving document chunks …")
    result = run_rag_tool(
        user_question=state["user_message"],
        conversation_history=state["conversation_history"],
    )
    print(f"[rag_node] {len(result['chunks'])} chunks retrieved from: {result['sources']}")
    return {"rag_result": result}


# ─────────────────────────────────────────────────────────────────────────────
# Node 2c — Web Search Tool Node
# ─────────────────────────────────────────────────────────────────────────────

def web_search_node(state: dict) -> dict:
    """
    Run Tavily search and synthesise an answer.
    """
    print("[web_node] Searching the web …")
    result = run_web_search_tool(
        user_question=state["user_message"],
        conversation_history=state["conversation_history"],
    )
    print(f"[web_node] {len(result['results'])} results for query: '{result['query']}'")
    return {"web_search_result": result}


# ─────────────────────────────────────────────────────────────────────────────
# Node 3 — Answer Synthesiser
# ─────────────────────────────────────────────────────────────────────────────

_SYNTHESISE_SYSTEM = """\
You are a friendly and precise e-commerce analytics assistant.
Your job is to deliver a clear, well-formatted final answer to the user.

Guidelines:
- Be concise but complete.
- If data comes from SQL results, summarise the key numbers first, then explain.
- If data comes from documents, cite the source.
- If data comes from web search, mention the URLs.
- Use markdown formatting where it aids readability (bullet lists, bold, tables).
- Maintain a helpful, professional tone.
"""

@trace(span_type="CHAIN", model="gpt-4o-mini")  # NEW: Add tracing
def synthesise_node(state: dict) -> dict:
    """
    Combine tool output into a polished final answer using GPT-4o-mini.
    - For SQL: synthesize narrative from raw rows
    - For RAG: synthesize answer from retrieved document chunks
    - For Web Search: synthesize answer from web search results
    """
    route = state.get("route", "")

    # ── SQL: tool returns raw rows — synthesise a narrative ─────────────────
    if route == "sql":
        sql_result = state.get("sql_result", {})
        sql_query  = sql_result.get("sql", "")
        table_md   = sql_result.get("table_md", "_No results_")
        error      = sql_result.get("error")

        if error:
            content = (
                f"The SQL query encountered an error:\n\n"
                f"```sql\n{sql_query}\n```\n\n"
                f"Error: {error}\n\n"
                "Please try rephrasing your question."
            )
        else:
            content = (
                f"SQL query executed:\n```sql\n{sql_query}\n```\n\n"
                f"Results:\n{table_md}"
            )

        messages = [{"role": "system", "content": _SYNTHESISE_SYSTEM}]
        messages.extend(state["conversation_history"][-4:])
        user_content = (
            f"Original question: {state['user_message']}\n\n"
            f"Query output:\n{content}\n\n"
            "Provide a clear, business-friendly summary of these results."
        )
        messages.append({"role": "user", "content": user_content})
        
        # Capture prompts as span inputs
        span = mlflow.get_current_active_span()
        if span:
            span.set_inputs({
                "system_prompt": _SYNTHESISE_SYSTEM,
                "user_prompt": user_content,
                "synthesis_type": "sql",
                "user_message": state['user_message']
            })
        
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
        answer = response.choices[0].message.content.strip()

    # ── RAG: synthesize answer from retrieved document chunks ───────────────
    elif route == "rag":
        rag_result = state.get("rag_result", {})
        chunks     = rag_result.get("chunks", [])
        sources    = rag_result.get("sources", [])

        if not chunks:
            answer = "I could not find relevant information in the loaded documents."
        else:
            # Build context block from retrieved chunks
            context_parts = []
            for i, chunk in enumerate(chunks, 1):
                context_parts.append(
                    f"[Excerpt {i} — {chunk['source']} (score: {chunk['score']:.3f})]:\n"
                    f"{chunk['text']}"
                )
            context = "\n\n---\n\n".join(context_parts)

            messages = [{"role": "system", "content": _SYNTHESISE_SYSTEM}]
            messages.extend(state["conversation_history"][-4:])
            user_content = (
                f"Document excerpts:\n\n{context}\n\n"
                f"Question: {state['user_message']}"
            )
            messages.append({"role": "user", "content": user_content})
            
            # Capture prompts as span inputs
            span = mlflow.get_current_active_span()
            if span:
                span.set_inputs({
                    "system_prompt": _SYNTHESISE_SYSTEM,
                    "user_prompt": user_content,
                    "synthesis_type": "rag",
                    "retrieval_sources": ", ".join(sources) if sources else "none",
                    "user_message": state['user_message']
                })

            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            answer = response.choices[0].message.content.strip()

            if sources:
                answer += f"\n\n_Sources: {', '.join(sources)}_"

    # ── Web Search: synthesize answer from search results ───────────────────
    elif route == "web_search":
        web_result = state.get("web_search_result", {})
        results    = web_result.get("results", [])
        query      = web_result.get("query", "")

        if not results:
            answer = "The web search returned no results for your query."
        else:
            # Format results for context
            result_blocks = []
            for i, r in enumerate(results, 1):
                block = (
                    f"[Result {i}]\n"
                    f"Title:   {r.get('title', 'N/A')}\n"
                    f"URL:     {r.get('url', 'N/A')}\n"
                    f"Snippet: {r.get('content', '')}"
                )
                result_blocks.append(block)
            formatted_results = "\n\n".join(result_blocks)

            messages = [{"role": "system", "content": _SYNTHESISE_SYSTEM}]
            messages.extend(state["conversation_history"][-4:])
            user_content = (
                f"Web search results for '{query}':\n\n{formatted_results}\n\n"
                f"Original question: {state['user_message']}\n\n"
                "Synthesize a clear, accurate answer from these results. "
                "Always mention the source URLs so the user can verify."
            )
            messages.append({"role": "user", "content": user_content})
            
            # Capture prompts as span inputs
            span = mlflow.get_current_active_span()
            if span:
                span.set_inputs({
                    "system_prompt": _SYNTHESISE_SYSTEM,
                    "user_prompt": user_content,
                    "synthesis_type": "web_search",
                    "web_search_query": query,
                    "user_message": state['user_message']
                })

            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            answer = response.choices[0].message.content.strip()

    else:
        answer = "I was unable to determine how to answer your question."

    print(f"[synthesise_node] Answer ready ({len(answer)} chars).")
    return {"final_answer": answer}


# ─────────────────────────────────────────────────────────────────────────────
# Node 4 — History Updater
# ─────────────────────────────────────────────────────────────────────────────

def update_history_node(state: dict) -> dict:
    """
    Append the current turn to conversation_history.
    (Turn number is already incremented in session.ask())
    """
    history = list(state["conversation_history"])
    history.append({"role": "user",      "content": state["user_message"]})
    history.append({"role": "assistant", "content": state["final_answer"]})
    return {
        "conversation_history": history,
        "turn_number": state.get("turn_number", 0),
    }
