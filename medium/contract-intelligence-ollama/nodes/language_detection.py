from langdetect import detect, LangDetectException

from models.state import ContractState


def detect_language_node(state: ContractState) -> dict:
    log = list(state.get("processing_log", []))
    text = state.get("full_text", "")

    try:
        sample = text[:3000] if len(text) > 3000 else text
        lang = detect(sample) if sample.strip() else "en"
    except LangDetectException:
        lang = "en"

    requires_translation = lang != "en"
    log.append(
        f"Language detected: {lang.upper()}"
        + (" – translation required" if requires_translation else "")
    )

    return {
        **state,
        "detected_language": lang,
        "requires_translation": requires_translation,
        "processing_log": log,
        "current_step": "translation" if requires_translation else "indexing",
    }
