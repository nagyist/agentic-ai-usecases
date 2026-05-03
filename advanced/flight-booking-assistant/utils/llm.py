import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment or .env file")
        _client = OpenAI(api_key=api_key)
    return _client


def call_llm(prompt: str) -> str:
    response = get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        timeout=30,
    )
    return response.choices[0].message.content.strip()


def call_llm_json(prompt: str) -> dict:
    response = get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
        timeout=30,
    )
    return json.loads(response.choices[0].message.content.strip())
