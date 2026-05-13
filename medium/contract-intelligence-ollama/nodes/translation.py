from typing import Tuple

from models.state import ContractState
from services.llm import LLMService

# Helsinki-NLP MarianMT model registry
MARIAN_MODELS = {
    "fr": "Helsinki-NLP/opus-mt-fr-en",
    "de": "Helsinki-NLP/opus-mt-de-en",
    "es": "Helsinki-NLP/opus-mt-es-en",
    "it": "Helsinki-NLP/opus-mt-it-en",
    "pt": "Helsinki-NLP/opus-mt-pt-en",
    "nl": "Helsinki-NLP/opus-mt-nl-en",
    "ru": "Helsinki-NLP/opus-mt-ru-en",
    "zh": "Helsinki-NLP/opus-mt-zh-en",
    "ja": "Helsinki-NLP/opus-mt-ja-en",
    "ko": "Helsinki-NLP/opus-mt-ko-en",
    "ar": "Helsinki-NLP/opus-mt-ar-en",
    "tr": "Helsinki-NLP/opus-mt-tr-en",
    "pl": "Helsinki-NLP/opus-mt-pl-en",
    "sv": "Helsinki-NLP/opus-mt-sv-en",
}

# Module-level cache so models load only once
_marian_cache: dict = {}


def _get_marian(model_name: str) -> Tuple:
    if model_name not in _marian_cache:
        from transformers import MarianMTModel, MarianTokenizer
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)
        _marian_cache[model_name] = (tokenizer, model)
    return _marian_cache[model_name]


def _translate_marian(text: str, lang: str) -> str:
    model_name = MARIAN_MODELS[lang]
    tokenizer, model = _get_marian(model_name)

    # Split into word-chunks that fit the model's 512-token limit
    words = text.split()
    chunk_words = 380
    word_chunks = [" ".join(words[i: i + chunk_words]) for i in range(0, len(words), chunk_words)]

    translated = []
    for chunk in word_chunks:
        inputs = tokenizer(chunk, return_tensors="pt", padding=True,
                           truncation=True, max_length=512)
        out = model.generate(**inputs)
        translated.append(tokenizer.decode(out[0], skip_special_tokens=True))

    return " ".join(translated)


def _translate_qwen(text: str, lang: str) -> str:
    llm = LLMService()
    max_chars = 2000
    parts = [text[i: i + max_chars] for i in range(0, len(text), max_chars)]
    results = []
    for part in parts:
        prompt = (
            f"Translate the following contract text from language code '{lang}' to English.\n"
            "Preserve all legal terminology, party names, dates, prices and structure exactly.\n\n"
            f"Text:\n{part}\n\nEnglish translation:"
        )
        results.append(llm.generate(prompt))
    return "\n".join(results)


def translation_node(state: ContractState) -> dict:
    log = list(state.get("processing_log", []))

    if not state.get("requires_translation"):
        return {**state, "translated_text": state.get("full_text", ""),
                "processing_log": log, "current_step": "indexing"}

    lang = state.get("detected_language", "en")
    text = state.get("full_text", "")
    method = "none"

    # Try MarianMT first; fall back to Qwen
    if lang in MARIAN_MODELS:
        try:
            translated = _translate_marian(text, lang)
            method = "MarianMT"
        except Exception as e:
            log.append(f"MarianMT failed ({e}), falling back to Qwen")
            try:
                translated = _translate_qwen(text, lang)
                method = "Qwen2.5-VL"
            except Exception as e2:
                log.append(f"Qwen translation failed ({e2}), keeping original")
                translated = text
    else:
        # Language not in MarianMT registry → go straight to Qwen
        try:
            translated = _translate_qwen(text, lang)
            method = "Qwen2.5-VL"
        except Exception as e:
            log.append(f"Translation failed ({e}), keeping original")
            translated = text

    log.append(f"Translation complete via {method} ({lang} → en)")
    return {
        **state,
        "translated_text": translated,
        "processing_log": log,
        "current_step": "indexing",
    }
