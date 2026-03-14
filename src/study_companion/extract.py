import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = PROJECT_ROOT / "data" / "raw" / "pdfs"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_JSON = PROCESSED_DIR / "questions.json"
CLEAN_QUESTIONS_JSON = PROJECT_ROOT / "data" / "interim" / "clean_questions_all.json"


def process_raw_pdfs():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    all_questions = []

    try:
        from .pdf_preprocessor import extract_text, extract_questions, extract_year_from_name

        pdf_files = sorted(PDF_DIR.glob("*.pdf"))
        for pdf_path in pdf_files:
            year = extract_year_from_name(pdf_path.name)
            raw_text = extract_text(str(pdf_path))
            questions = extract_questions(raw_text, year)
            for question in questions:
                question["source_file"] = pdf_path.name
            print(f"{pdf_path.name}: extracted {len(questions)} questions.")
            all_questions.extend(questions)
    except Exception as exc:
        if CLEAN_QUESTIONS_JSON.exists():
            with open(CLEAN_QUESTIONS_JSON, "r") as f:
                all_questions = json.load(f)
            for q in all_questions:
                q.setdefault("solution_text", "")
            print(
                "PDF parser unavailable; loaded existing clean_questions_all.json "
                f"({len(all_questions)} questions). Reason: {exc}"
            )
        else:
            raise RuntimeError(
                "PDF parsing is unavailable and clean_questions_all.json is missing."
            ) from exc

    with open(PROCESSED_JSON, "w") as f:
        json.dump(all_questions, f, indent=4)

    print(f"Wrote {len(all_questions)} questions to {PROCESSED_JSON}")
    return all_questions
