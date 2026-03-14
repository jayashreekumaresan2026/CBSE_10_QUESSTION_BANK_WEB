import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = PROJECT_ROOT / "data" / "raw" / "pdfs"
OUTPUT_FILE = PROJECT_ROOT / "data" / "interim" / "clean_questions_all.json"

def extract_text(pdf_path):
    # Try PyMuPDF first; fall back to pdfplumber if local binary deps are missing.
    try:
        import fitz

        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception:
        import pdfplumber

        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return text

def extract_questions(text, year):
    # Start from the first section to avoid matching numbered instructions.
    section_start = re.search(r"SECTION\s*(?:[–-]\s*)?A\b", text, flags=re.IGNORECASE)
    text_to_parse = text[section_start.start():] if section_start else text

    # Prefer explicit "Question N." markers when available.
    question_marker_pattern = re.compile(r"(?mi)^\s*Question\s+(\d+)\.\s+")
    matches = list(question_marker_pattern.finditer(text_to_parse))

    # Fallback for other paper formats: "Q-1 ..." or "3. ..."
    if not matches:
        marker_pattern = re.compile(
                r"(?mi)^\s*(?:Q\s*[-–]?\s*(\d+)|(\d+)\.)\s*"
        )
        matches = list(marker_pattern.finditer(text_to_parse))
    questions = []
    seen_numbers = set()

    for i, match in enumerate(matches):
        number = next((g for g in match.groups() if g), None)
        if not number:
            continue

        number = int(number)

        # Only allow real question numbers
        if number < 1 or number > 34:
            continue

        # Avoid duplicates
        if number in seen_numbers:
            continue

        seen_numbers.add(number)

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text_to_parse)
        block = text_to_parse[start:end]

        parts = re.split(r"(?i)\bsolution\s*:", block, maxsplit=1)
        question_text = parts[0].strip()
        solution_text = parts[1].strip() if len(parts) > 1 else ""

        # Filter out very small garbage blocks
        if len(question_text) < 40:
            continue

        questions.append({
            "year": year,
            "question_number": number,
            "question_text": question_text,
            "solution_text": solution_text
        })

    return questions

def extract_year_from_name(filename):
    year_match = re.search(r"(20\d{2})", filename)
    return int(year_match.group(1)) if year_match else None

if __name__ == "__main__":
    all_questions = []
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in: {PDF_DIR}")
    for pdf_path in pdf_files:
        year = extract_year_from_name(pdf_path.name)
        raw_text = extract_text(str(pdf_path))
        questions = extract_questions(raw_text, year)
        for question in questions:
            question["source_file"] = pdf_path.name

        print(f"{pdf_path.name}: extracted {len(questions)} questions.")
        all_questions.extend(questions)

    if all_questions:
        print(f"Total extracted questions: {len(all_questions)}")
    else:
        print("No questions found. Check PDF format and extraction patterns.")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_questions, f, indent=4)
