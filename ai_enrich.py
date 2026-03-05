import json
import urllib.request
from pathlib import Path
from urllib.error import URLError

INPUT_FILE = Path("data/processed/questions.json")
OUTPUT_FILE = Path("data/processed/questions_enriched.json")
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"


def ask_ollama(question_text, source_file):
    prompt = (
        "You are classifying CBSE Class 10 exam questions.\n"
        "Return strict JSON with keys: subject, chapter.\n"
        "subject should be one of: Mathematics, Science, Social Science, English, Hindi, General.\n"
        "chapter should be a book chapter name for that subject.\n"
        f"Source file: {source_file}\n"
        f"Question: {question_text}\n"
    )
    payload = json.dumps(
        {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"}
    ).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        body = json.loads(response.read().decode("utf-8"))
        return json.loads(body.get("response", "{}"))


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_FILE}")

    with open(INPUT_FILE, "r") as f:
        questions = json.load(f)

    enriched = []
    for i, q in enumerate(questions, start=1):
        base = dict(q)
        try:
            meta = ask_ollama(base.get("question_text", ""), base.get("source_file", ""))
            base["subject"] = meta.get("subject", "General")
            base["chapter"] = meta.get("chapter", "General")
        except (URLError, TimeoutError, json.JSONDecodeError):
            base["subject"] = base.get("subject", "General")
            base["chapter"] = base.get("chapter", "General")
        enriched.append(base)
        if i % 10 == 0:
            print(f"Processed {i}/{len(questions)}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(enriched, f, indent=2)
    print(f"Wrote {len(enriched)} enriched questions to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
