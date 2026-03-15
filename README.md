
# CBSE Class 10 Question Bank & Study Companion

A powerful, data-driven tool designed to help CBSE Class 10 students master their exams by focusing on **chapter-wise repeated questions** from the last 10+ years of board papers.

## 🚀 Business Context
The **CBSE Class 10 Question Bank** automates the extraction and analysis of previous year question papers. It provides students with:
- **Multi-Subject Support**: Comprehensive coverage of Mathematics, Science, Social Science, and English.
- **Repeated Question Detection**: Intelligent similarity clustering identifies which questions appear most frequently across different years.
- **Smart Categorization**: Automatically groups questions into chapters and topics, even when not explicitly labeled in the source PDFs.
- **High-Quality Rendering**: Full support for complex Mathematical equations and Chemical formulas using LaTeX (KaTeX).
- **Progress Tracking**: Help students monitor their revision status (`Not Started`, `Practicing`, `Mastered`).

---

## 🛠 Technical Architecture
The project is split into two main components:
1.  **Data Processing Pipeline (Python)**: Extracts raw text from PDFs, cleans mathematical/chemical notation, clusters similar questions, and generates structured JSON datasets.
2.  **Web Dashboard (Static/Cloudflare)**: A modern, fast, and responsive UI that loads the processed JSON data. It's designed for high performance and easy deployment.
3.  **Interactive App (Streamlit)**: A secondary Python-based dashboard for local analysis and progress tracking.

---

## 💻 Local Setup & Development

### 1. Prerequisites
- Python 3.10 or higher
- Node.js (for local web preview)

### 2. Installation
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Build/Refresh Data
The data is extracted directly from PDF files located in `data/raw/pdfs/`.
```bash
# Step 1: Extract questions from PDFs to a central JSON
python3 scripts/build_questions_json.py

# Step 2: Clean, categorize, and build subject-specific datasets for the web
python3 scripts/build_subject_data.py
```

### 4. Run the Web Dashboard Locally
```bash
cd web
python3 -m http.server 8000
# Open http://localhost:8000
```

### 5. Run the Streamlit App (Alternative UI)
```bash
streamlit run app.py
```

---

## ☁️ Cloudflare Pages Deployment

This project is optimized for **Cloudflare Pages**. It uses a custom build command to process the PDFs and generate the static site on the fly.

### 🌐 GitHub Integration (Recommended)
1.  Connect your GitHub repository to Cloudflare Pages.
2.  **Project Type**: Select **Pages** (NOT Workers).
3.  **Build Settings**:
    -   **Framework preset**: `None`
    -   **Build command**: `pip install -r requirements.txt && python3 scripts/build_questions_json.py && python3 scripts/build_subject_data.py`
    -   **Build output directory**: `web`
    -   **Root directory**: Leave BLANK (or `/`)
4.  **Environment Variables**:
    -   Add `PYTHON_VERSION`: `3.11` (or higher) if needed.

### 🛠 CLI Deployment (Manual)
```bash
# Ensure you have wrangler installed
npm install -g wrangler

# Deploy the web directory
wrangler pages deploy web
```

---

## 📂 Project Structure
-   `scripts/`: Python scripts for data extraction and processing.
    -   `build_questions_json.py`: PDF extraction logic.
    -   `build_subject_data.py`: Advanced cleaning, LaTeX formatting, and similarity clustering.
-   `src/`: Core library for PDF processing and UI components.
-   `web/`: Static website assets (HTML, JS, CSS) and generated `data/*.json`.
-   `data/raw/pdfs/`: Organized by subject (maths, science, social, english).
-   `wrangler.toml`: Deployment configuration for Cloudflare Pages.

---

## 📝 Important Notes
-   **Math/Science Notation**: The pipeline uses advanced Regex to repair corrupted PDF text into proper LaTeX (e.g., `$\sqrt{2}$`, `$H_2O$`).
-   **Repeated Questions**: A question is marked as "REPEATED" if its similarity score exceeds 0.82 compared to other questions in the same chapter.
-   **Deployment**: Always use `wrangler pages deploy` for this project. The standard `wrangler deploy` is for Workers and will fail.
