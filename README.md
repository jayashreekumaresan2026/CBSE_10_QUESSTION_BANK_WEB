
# CBSE Study Companion (Chapter-wise Repeated Questions)

Streamlit app to help students revise **chapter-wise repeated questions** from previous year papers.

It supports:
- Subject and chapter-wise grouping
- Repeated-question detection across years
- Year-wise filtering
- Question + solution lookup by year and question number
- Progress tracking (`Not Started`, `Practicing`, `Mastered`)
- Priority ranking of repeated questions

## Project Structure

- `app.py`: Streamlit entrypoint (imports code from `src/`)
- `src/study_companion/`: App + pipeline modules
- `scripts/preprocess.py`: Pipeline entrypoint (extract PDFs -> JSON -> DB)
- `data/raw/pdfs/`: Input PDFs
- `data/interim/clean_questions_all.json`: Optional extracted raw dump (fallback)
- `data/processed/questions.json`: Main processed dataset used by UI
- `data/processed/questions_enriched.json`: Optional AI-enriched dataset
- `data/processed/progress.json`: Saved progress from UI (local)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Build/Refresh Data

```bash
python3 scripts/preprocess.py
```

This will:
1. Parse PDFs from `data/raw/pdfs/`
2. Extract question text and solution text
3. Save processed data to `data/processed/questions.json`
4. Insert records into `data/processed/repeated_questions.db`

## Run Locally

```bash
streamlit run app.py --server.port 8501
```

Open: `http://localhost:8501`

## Optional AI Enrichment (Ollama)

If you want AI-based subject/chapter tagging:

1. Start Ollama locally
2. Ensure model exists (default: `qwen2.5:3b`)
3. Run:

```bash
./.venv/bin/python ai_enrich.py
```

The app will automatically prefer `data/processed/questions_enriched.json` if present.

## Streamlit Community Cloud Deployment

1. Push this project to GitHub
2. Ensure these files are in repo:
   - `app.py`
   - `requirements.txt`
   - `data/processed/questions.json` (and optionally `questions_enriched.json`)
3. In Streamlit Community Cloud:
   - New app -> choose repo
   - Main file path: `app.py`
   - Deploy

After deploy, you can use it from web/mobile browser anywhere.

## Notes

- If some solutions are missing, re-run `preprocess.py` after updating PDFs.
- Current chapter rules are strongest for Mathematics; other subjects improve with AI enrichment.
