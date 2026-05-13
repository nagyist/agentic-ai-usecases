import json
import re
import base64
from typing import Optional, List

import ollama

from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL


class LLMService:
    def __init__(self, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.client = ollama.Client(host=base_url)

    def generate(self, prompt: str, images: Optional[List[str]] = None) -> str:
        message: dict = {"role": "user", "content": prompt}

        if images:
            encoded = []
            for img_path in images:
                with open(img_path, "rb") as f:
                    encoded.append(base64.b64encode(f.read()).decode("utf-8"))
            message["images"] = encoded

        response = self.client.chat(model=self.model, messages=[message])
        return response.message.content

    def generate_json(self, prompt: str, images: Optional[List[str]] = None) -> dict:
        full_prompt = (
            prompt
            + "\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "No markdown code blocks, no explanation, just the JSON object."
        )
        raw = self.generate(full_prompt, images)
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        # Strip markdown fences
        for fence in ("```json", "```"):
            if text.startswith(fence):
                text = text[len(fence):]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract first {...} block
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {}
