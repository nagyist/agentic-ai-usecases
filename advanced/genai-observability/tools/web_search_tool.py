# tools/web_search_tool.py
# ─────────────────────────────────────────────────────────────────────────────
# Web Search Tool: uses Serper API to fetch live web results.
#
# Serper returns structured results (title, link, snippet) — much
# cleaner than raw HTML scraping for LLM consumption.
#
# NOTE: This tool only retrieves raw search results. Answer synthesis
# is handled by the central synthesis node.
# ─────────────────────────────────────────────────────────────────────────────

import requests
from config import SERPER_API_KEY
from observability import trace  # NEW: Import observability

@trace(span_type="TOOL", attributes={  # NEW: Add tracing
    "api.provider": "serper.dev",
    "api.endpoint": "google.serper.dev/search",
})
def run_web_search_tool(user_question: str, conversation_history: list[dict]) -> dict:
    """
    Main entry point for the Web Search tool.

    Steps:
      1. Call Serper API to search the web
      2. Return raw results for synthesis node to handle

    Returns a dict:
      {
        "results": list[dict],   # raw Serper results [{title, url, content}]
        "query":   str,          # the query sent to Serper
      }
    """
    # ── 1. Web search ─────────────────────────────────────────────────────────
    try:
        if not SERPER_API_KEY:
            return {
                "results": [],
                "query": user_question,
            }
        
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {"q": user_question, "num": 5}
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {
                "results": [],
                "query": user_question,
            }
        
        data = response.json()
        raw_results = []
        
        # Extract organic results
        for item in data.get("organic", [])[:5]:
            raw_results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "content": item.get("snippet")
            })
    except Exception as exc:
        print(f"[web_search_tool] Error: {exc}")
        return {
            "results": [],
            "query": user_question,
        }

    return {
        "results": raw_results,
        "query": user_question,
    }
