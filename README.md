
# CBSE Study Companion (Chapter-wise Repeated Questions)

Streamlit app to help students revise **chapter-wise repeated questions** from previous year papers.

It supports:
- Subject and chapter-wise grouping
- Repeated-question detection across years
- Year-wise filtering
- Question + solution lookup by year and question number
- Progress tracking (`Not Started`, `Practicing`, `Mastered`)
- Priority ranking of repeated questions

## Static Web Dashboard (Cloudflare Pages)

The project also includes a modern, fast static web dashboard located in the `web/` directory.

### Build the static data
To refresh the JSON data for the web dashboard, run:
```bash
python3 scripts/build_questions_json.py  # Extract from PDFs
python3 scripts/build_subject_data.py      # Build all subject datasets
```

### Run Web Dashboard locally
```bash
cd web
npx serve .
```

### Deploy to Cloudflare Pages
You can deploy the `web/` directory directly to Cloudflare Pages.
The `wrangler.toml` is already configured for the project.

**Option A: Automated CLI Deployment**
1. Install Wrangler CLI: `npm install -g wrangler`
2. Login: `wrangler login`
3. Deploy: `wrangler pages deploy web`

**Option B: GitHub Integration (Recommended)**
1. Push this project to a GitHub repository.
2. In the Cloudflare Dashboard: **Workers & Pages** > **Create application** > **Pages** > **Connect to Git**.
3. Select your repository.
4. Set **Build command** to: `python3 scripts/build_questions_json.py && python3 scripts/build_subject_data.py`
5. Set **Build output directory** to: `web`
6. Click **Save and Deploy**.

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
