import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from hashlib import md5
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_JSON = PROJECT_ROOT / "data" / "processed" / "questions.json"
ENRICHED_JSON = PROJECT_ROOT / "data" / "processed" / "questions_enriched.json"
PROGRESS_JSON = PROJECT_ROOT / "data" / "processed" / "progress.json"
STATUS_OPTIONS = ["Not Started", "Practicing", "Mastered"]

MATH_CHAPTER_RULES = [
    ("Real Numbers", ["hcf", "lcm", "euclid", "fundamental theorem of arithmetic"]),
    ("Polynomials", ["polynomial", "zeroes", "quadratic polynomial"]),
    ("Pair of Linear Equations", ["pair of linear equations", "linear equation", "elimination", "substitution"]),
    ("Quadratic Equations", ["quadratic equation", "discriminant", "roots of"]),
    ("Arithmetic Progressions", ["a.p.", "ap", "arithmetic progression", "common difference"]),
    ("Triangles", ["triangle", "similar triangles", "pythagoras"]),
    ("Coordinate Geometry", ["coordinates", "distance formula", "section formula", "midpoint"]),
    ("Trigonometry", ["sin", "cos", "tan", "trigonometry", "angle of elevation", "angle of depression"]),
    ("Circles", ["circle", "tangent", "chord", "radius", "diameter"]),
    ("Areas Related to Circles", ["sector", "segment", "area of circle", "circumference"]),
    ("Surface Areas and Volumes", ["cylinder", "cone", "sphere", "hemisphere", "frustum", "volume", "surface area"]),
    ("Statistics", ["mean", "median", "mode", "frequency", "ogive", "histogram"]),
    ("Probability", ["probability", "coin", "dice", "card", "at random"]),
]


def load_questions():
    source_file = ENRICHED_JSON if ENRICHED_JSON.exists() else PROCESSED_JSON
    if not source_file.exists():
        return []
    with open(source_file, "r") as f:
        return json.load(f)


def load_progress():
    if not PROGRESS_JSON.exists():
        return {}
    with open(PROGRESS_JSON, "r") as f:
        return json.load(f)


def save_progress(progress):
    PROGRESS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_JSON, "w") as f:
        json.dump(progress, f, indent=2)


def normalize_text(text):
    cleaned = (text or "").lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def clean_question_text(text):
    text = (text or "").strip()
    return re.sub(r"^[\s\.:;,\-]+", "", text)


def infer_subject(source_file):
    name = (source_file or "").lower()
    if "math" in name:
        return "Mathematics"
    if "science" in name:
        return "Science"
    if "social" in name or "sst" in name:
        return "Social Science"
    if "english" in name:
        return "English"
    if "hindi" in name:
        return "Hindi"
    return "General"


def infer_chapter(subject, question_text):
    text = normalize_text(question_text)
    if subject == "Mathematics":
        for chapter, keywords in MATH_CHAPTER_RULES:
            if any(k in text for k in keywords):
                return chapter
        return "Other Maths"
    return "General"


def prepare_records(raw):
    records = []
    for q in raw:
        subject = q.get("subject") or infer_subject(q.get("source_file", ""))
        chapter = q.get("chapter") or infer_chapter(subject, q.get("question_text", ""))
        rec = dict(q)
        rec["subject"] = subject
        rec["chapter"] = chapter
        rec["year"] = str(rec.get("year", ""))
        rec["question_number"] = str(rec.get("question_number", ""))
        rec["question_text"] = clean_question_text(rec.get("question_text", ""))
        rec["norm_text"] = normalize_text(rec.get("question_text", ""))
        key_source = f"{rec['subject']}|{rec['year']}|{rec['question_number']}|{rec['norm_text'][:200]}"
        rec["question_id"] = md5(key_source.encode("utf-8")).hexdigest()[:16]
        records.append(rec)
    return records


def group_repeats(records, threshold=0.93):
    # Cluster within the same subject+chapter using fuzzy similarity.
    grouped = defaultdict(list)
    for r in records:
        key = (r["subject"], r["chapter"])
        grouped[key].append(r)

    clusters = []
    for (subject, chapter), items in grouped.items():
        local = []
        for item in items:
            assigned = False
            for cl in local:
                rep = cl[0]["norm_text"]
                if rep and item["norm_text"]:
                    sim = SequenceMatcher(None, rep, item["norm_text"]).ratio()
                    if sim >= threshold:
                        cl.append(item)
                        assigned = True
                        break
            if not assigned:
                local.append([item])

        for idx, cl in enumerate(local, start=1):
            years = sorted({x["year"] for x in cl if x["year"]})
            repeated = len(years) > 1
            cluster_id = f"{subject}|{chapter}|{idx}"
            max_year = max([int(y) for y in years if y.isdigit()], default=0)
            for x in cl:
                x["cluster_id"] = cluster_id
                x["repeated_years"] = ", ".join(years) if years else "-"
                x["is_repeated"] = repeated
                x["repeat_count"] = len(years)
                x["priority_score"] = len(years) * 10 + (max_year / 1000.0)
            clusters.append(
                {
                    "cluster_id": cluster_id,
                    "subject": subject,
                    "chapter": chapter,
                    "years": years,
                    "is_repeated": repeated,
                    "items": cl,
                }
            )
    return records, clusters


def priority_label(score):
    if score >= 30:
        return "High"
    if score >= 20:
        return "Medium"
    return "Low"


def chapter_summary(clusters, subject):
    rows = []
    by_chapter = defaultdict(list)
    for c in clusters:
        if c["subject"] == subject:
            by_chapter[c["chapter"]].append(c)
    for chapter, cls in sorted(by_chapter.items()):
        repeated_clusters = [c for c in cls if c["is_repeated"]]
        year_union = sorted({y for c in repeated_clusters for y in c["years"]})
        rows.append(
            {
                "chapter": chapter,
                "repeated_question_groups": len(repeated_clusters),
                "years_covered": ", ".join(year_union) if year_union else "-",
            }
        )
    return rows


def with_progress(records, progress):
    for r in records:
        r["status"] = progress.get(r["question_id"], "Not Started")
        r["priority"] = priority_label(r.get("priority_score", 0))
    return records


def dashboard_summary(records, subject):
    subject_records = [r for r in records if r["subject"] == subject]
    by_status = defaultdict(int)
    by_chapter_total = defaultdict(int)
    by_chapter_mastered = defaultdict(int)
    repeated_count = 0
    for r in subject_records:
        by_status[r["status"]] += 1
        by_chapter_total[r["chapter"]] += 1
        if r["status"] == "Mastered":
            by_chapter_mastered[r["chapter"]] += 1
        if r.get("is_repeated"):
            repeated_count += 1
    completion_rows = []
    for chapter in sorted(by_chapter_total):
        total = by_chapter_total[chapter]
        mastered = by_chapter_mastered[chapter]
        completion = round((mastered / total) * 100, 1) if total else 0.0
        completion_rows.append(
            {
                "chapter": chapter,
                "mastered": mastered,
                "total": total,
                "completion_%": completion,
            }
        )
    return subject_records, by_status, completion_rows, repeated_count


def run_app():
    st.set_page_config(page_title="Chapter-wise Repeated Questions", layout="wide")
    st.title("Study Companion: Chapter-wise Repeated Questions")

    raw = load_questions()
    if not raw:
        st.error("No processed data found at data/processed/questions.json")
        st.info("Run: ./\.venv/bin/python preprocess.py")
        return

    progress = load_progress()
    records, clusters = group_repeats(prepare_records(raw))
    records = with_progress(records, progress)

    subjects = sorted({r["subject"] for r in records})
    years = sorted({r["year"] for r in records if r["year"]})
    all_repeated = [r for r in records if r.get("is_repeated")]

    col1, col2, col3 = st.columns(3)
    subject = col1.selectbox("Subject", options=subjects, index=0)
    year_filter = col2.selectbox("Year", options=["All"] + years, index=0)
    repeated_only = col3.checkbox("Only repeated questions", value=True)

    tab_dash, tab_study, tab_lookup = st.tabs(["Dashboard", "Study", "Lookup"])

    with tab_dash:
        subject_records, by_status, completion_rows, repeated_count = dashboard_summary(records, subject)
        mastered = by_status.get("Mastered", 0)
        total = len(subject_records)
        progress_pct = round((mastered / total) * 100, 1) if total else 0.0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Questions", total)
        m2.metric("Repeated Questions", repeated_count)
        m3.metric("Mastered", mastered)
        m4.metric("Completion %", f"{progress_pct}%")

        st.subheader("Status Distribution")
        status_rows = [{"status": s, "count": by_status.get(s, 0)} for s in STATUS_OPTIONS]
        st.dataframe(status_rows, use_container_width=True, height=180)
        st.bar_chart({row["status"]: row["count"] for row in status_rows})

        st.subheader("Chapter Completion")
        st.dataframe(completion_rows, use_container_width=True, height=260)

        st.subheader("Top Priority Repeated Questions")
        top_priority = sorted(
            [r for r in subject_records if r.get("is_repeated")],
            key=lambda x: x.get("priority_score", 0),
            reverse=True,
        )[:20]
        st.dataframe(
            [
                {
                    "chapter": r["chapter"],
                    "year": r["year"],
                    "question_number": r["question_number"],
                    "repeated_years": r.get("repeated_years", "-"),
                    "priority": r.get("priority", "Low"),
                    "status": r.get("status", "Not Started"),
                    "question_text": r.get("question_text", ""),
                }
                for r in top_priority
            ],
            use_container_width=True,
            height=320,
        )

    with tab_study:
        chapter_rows = chapter_summary(clusters, subject)
        st.subheader("Chapter-wise Repeated Coverage")
        st.dataframe(chapter_rows, use_container_width=True, height=230)

        chapter_options = [r["chapter"] for r in chapter_rows] or ["General"]
        chapter = st.selectbox("Choose chapter for study", options=chapter_options)

        visible = [r for r in records if r["subject"] == subject and r["chapter"] == chapter]
        if year_filter != "All":
            visible = [r for r in visible if r["year"] == year_filter]
        if repeated_only:
            visible = [r for r in visible if r.get("is_repeated")]

        st.write(f"Questions shown: {len(visible)}")
        st.dataframe(
            [
                {
                    "year": r["year"],
                    "question_number": r["question_number"],
                    "priority": r.get("priority", "Low"),
                    "status": r.get("status", "Not Started"),
                    "repeated_years": r.get("repeated_years", "-"),
                    "question_text": r.get("question_text", ""),
                }
                for r in visible
            ],
            use_container_width=True,
            height=360,
        )

        st.subheader("Update Progress")
        if visible:
            labels = [
                f"{idx + 1}. {r['year']} Q{r['question_number']} [{r.get('priority','Low')}]"
                for idx, r in enumerate(visible)
            ]
            selected = st.selectbox("Pick a question", options=range(len(visible)), format_func=lambda i: labels[i])
            picked = visible[selected]
            new_status = st.radio(
                "Set status",
                options=STATUS_OPTIONS,
                horizontal=True,
                index=STATUS_OPTIONS.index(picked.get("status", "Not Started")),
            )
            if st.button("Save Status"):
                progress[picked["question_id"]] = new_status
                save_progress(progress)
                st.success("Progress updated.")
                st.rerun()

            st.text_area("Question", picked.get("question_text", ""), height=170)
            sol = picked.get("solution_text", "")
            if sol:
                st.text_area("Solution", sol, height=220)
            else:
                st.info("Solution not available for this question in current dataset.")
        else:
            st.info("No questions for selected filters.")

    with tab_lookup:
        st.subheader("Get Question + Solution by Year and Number")
        c1, c2 = st.columns(2)
        pick_year = c1.selectbox("Select year", options=years)
        pick_qn = c2.text_input("Enter question number", "")

        if st.button("Show", key="lookup_show"):
            match = None
            for r in records:
                if r["subject"] != subject:
                    continue
                if r["year"] == str(pick_year) and r["question_number"] == str(pick_qn).strip():
                    match = r
                    break
            if not match:
                st.error("No matching question found.")
            else:
                st.write(f"Chapter: {match['chapter']}")
                st.write(f"Priority: {match.get('priority', 'Low')}")
                st.write(f"Repeated in years: {match.get('repeated_years', '-')}")
                st.write(f"Current status: {match.get('status', 'Not Started')}")
                st.text_area("Question", match.get("question_text", ""), height=180)
                sol = match.get("solution_text", "")
                if sol:
                    st.text_area("Solution", sol, height=220)
                else:
                    st.warning("Solution not available for this question in current dataset.")


if __name__ == "__main__":
    run_app()
