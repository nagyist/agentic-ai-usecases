import os
import json
import time
import inspect
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = None
_run_logs: list = []


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment or .env file")
        _client = OpenAI(api_key=api_key)
    return _client


def reset_logs():
    global _run_logs
    _run_logs = []


def get_logs() -> list:
    return list(_run_logs)


def log_node(node: str, details: dict, latency_ms: int = 0):
    """Log a non-LLM node execution (validation, routing, DB lookup, etc.)."""
    _run_logs.append({
        "node": node,
        "call_type": "node",
        "latency_ms": latency_ms,
        "details": details,
    })


def _caller_node() -> str:
    """Walk up the call stack to find the first frame outside llm.py."""
    for frame_info in inspect.stack()[2:]:
        fname = os.path.basename(frame_info.filename)
        if fname != "llm.py":
            node = fname.replace(".py", "")
            return f"{node}.{frame_info.function}"
    return "unknown"


def call_llm(prompt: str) -> str:
    model = "gpt-4o-mini"
    node = _caller_node()
    t0 = time.time()
    response = get_client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        timeout=30,
    )
    latency_ms = round((time.time() - t0) * 1000)
    output = response.choices[0].message.content.strip()
    usage = response.usage
    _run_logs.append({
        "node": node,
        "model": model,
        "prompt": prompt,
        "output": output,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "latency_ms": latency_ms,
        "call_type": "text",
    })
    return output


def call_llm_json(prompt: str) -> dict:
    model = "gpt-4o-mini"
    node = _caller_node()
    t0 = time.time()
    response = get_client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
        timeout=30,
    )
    latency_ms = round((time.time() - t0) * 1000)
    raw = response.choices[0].message.content.strip()
    usage = response.usage
    _run_logs.append({
        "node": node,
        "model": model,
        "prompt": prompt,
        "output": raw,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "latency_ms": latency_ms,
        "call_type": "json",
    })
    return json.loads(raw)
