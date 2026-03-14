import json
import urllib.request
from urllib.error import URLError

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"


def _default_classification():
    return {
        "chapter": "General",
        "topic": "General",
        "question_type": "Unknown",
        "marks_type": "Unknown",
        "difficulty": "Unknown",
    }


def classify_question(question_data, use_ollama=False, model=OLLAMA_MODEL):
    if not use_ollama:
        return _default_classification()

    prompt = (
        "Classify this CBSE maths question into JSON fields: chapter, topic, "
        "question_type, marks_type, difficulty.\n\nQuestion:\n"
        f"{question_data.get('question_text', '')}\n\nReturn only JSON."
    )
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
            model_text = body.get("response", "{}")
            parsed = json.loads(model_text)
            base = _default_classification()
            base.update({k: v for k, v in parsed.items() if k in base})
            return base
    except (URLError, TimeoutError, json.JSONDecodeError):
        return _default_classification()
