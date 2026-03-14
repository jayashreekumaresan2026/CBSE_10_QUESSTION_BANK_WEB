import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, Float, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Question(Base):
    __tablename__ = 'question'

    id = Column(Integer, primary_key=True)
    year = Column(String)
    question_number = Column(Integer)
    question_text = Column(String)
    source_file = Column(String)


class RepeatedQuestion(Base):
    __tablename__ = 'repeated_question'

    id = Column(Integer, primary_key=True)
    chapter = Column(String)
    topic = Column(String)
    question_type = Column(String)
    marks_type = Column(String)
    difficulty = Column(String)
    year1 = Column(String)
    year2 = Column(String)
    frequency = Column(Float)


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

    repeated_questions = group_repeated_questions(question)
    for i, repeat in enumerate(repeated_questions):
        conn.execute(
            RepeatedQuestion.__table__.insert(),
            dict(chapter=repeat.chapter,
                 topic=repeat.topic,
                 question_type=repeat.question_type,
                 marks_type=repeat.marks_type,
                 difficulty=repeat.difficulty,
                 year1=repeat.year1,
                 year2=repeat.year2,
                 frequency=repeat.frequency)
        )


def connect_to_db():
    return sqlite3.connect(':memory:')