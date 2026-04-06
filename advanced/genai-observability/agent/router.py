# agent/router.py
# ─────────────────────────────────────────────────────────────────────────────
# Router: uses GPT-4o-mini to classify every user message into one of three
# routes before handing off to the appropriate tool node.
#
# Routes:
#   sql        → query the local SQLite e-commerce database
#   rag        → search loaded PDF documents
#   web_search → live internet search via Tavily
# ─────────────────────────────────────────────────────────────────────────────

import json
import re
import mlflow
from openai import OpenAI
from config import LLM_MODEL, OPENAI_API_KEY, ROUTES
from observability import trace  # NEW: Import observability

client = OpenAI(api_key=OPENAI_API_KEY)

ROUTER_SYSTEM = """\
You are a routing agent for an e-commerce analytics assistant.
Given a user message and conversation history, you must decide which tool to use.

AVAILABLE TOOLS:
  sql        — Use when the question asks about data that lives in the database:
               orders, order items, customers, payments, products, revenue,
               counts, aggregations, trends, specific orders/customers, SQL-style
               queries over structured e-commerce data.

  rag        — Use when the question asks about information in uploaded documents:
               policies, manuals, documentation, FAQs, anything the user has
               uploaded as a PDF. If no PDFs are loaded this still applies.

  web_search — Use when the question:
               • asks about current events, news, or real-time information
               • is about general e-commerce industry trends or benchmarks
               • cannot be answered from the database or PDF documents
               • asks "what is", "how does X work", or general knowledge questions

OUTPUT FORMAT (respond with ONLY valid JSON, no other text):
{
  "route": "<sql|rag|web_search>",
  "reason": "<one-sentence explanation>"
}
"""

@trace(span_type="PARSER", model="gpt-4o-mini")
def route_question(user_message: str, conversation_history: list[dict]) -> dict:
    """
    Classify user_message into one of ROUTES.

    Returns:
      {
        "route":  str,   # one of "sql", "rag", "web_search"
        "reason": str,   # routing rationale
      }
    """
    messages = [{"role": "system", "content": ROUTER_SYSTEM}]

    # Add brief conversation context (last 4 messages = 2 turns)
    for msg in conversation_history[-4:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})
    
    # Capture system and user prompts as span inputs
    span = mlflow.get_current_active_span()
    if span:
        span.set_inputs({
            "system_prompt": ROUTER_SYSTEM,
            "user_prompt": user_message,
            "conversation_context": conversation_history[-4:]
        })

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.0,
        max_tokens=128,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: extract route from raw text
        for route in ROUTES:
            if route in raw.lower():
                return {"route": route, "reason": "extracted from malformed JSON"}
        return {"route": "web_search", "reason": "could not parse router output"}

    route = parsed.get("route", "web_search").lower().strip()
    if route not in ROUTES:
        route = "web_search"

    return {
        "route":  route,
        "reason": parsed.get("reason", ""),
    }
