import os
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from extract import process_raw_pdfs
from classify import classify_question
from database import Base, Question

PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_PATH = PROCESSED_DIR / "repeated_questions.db"
DB_URL = f"sqlite:///{DB_PATH}"


def initialize_db(engine):
    Base.metadata.create_all(bind=engine)


def add_question_to_db(conn, question):
    conn.execute(
        Question.__table__.insert(),
        dict(year=question['year'],
             question_number=question['question_number'],
             question_text=question['question_text'],
             source_file=question['source_file'])
    )


def connect_to_db():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal


if __name__ == "__main__":
    engine, SessionLocal = connect_to_db()
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    # Process raw PDFs and store questions in JSON format.
    questions = process_raw_pdfs()

    # Insert extracted questions into SQLite.
    for q_data in questions:
        # Keep classification call for future use; current return is safe fallback unless use_ollama=True.
        _ = classify_question(q_data, use_ollama=False)
        add_question_to_db(session, q_data)

    session.commit()
    session.close()
    print(f"Inserted {len(questions)} questions into {DB_PATH}")
