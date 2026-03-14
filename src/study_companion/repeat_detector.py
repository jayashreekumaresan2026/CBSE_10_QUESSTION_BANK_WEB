import pandas as pd
from sentence_transformers import SentenceTransformer, util


def detect_repeated_questions(questions_df):
    transformer = SentenceTransformer('all-MiniLM-L6-v2')

    # Generate embeddings for each question
    for _, row in questions_df.iterrows():
        embedding = transformer.encode(row["question_text"])

        # Placeholder for storing repeated questions
        repeat_df = pd.DataFrame()

        if not repeat_df.empty:
            similarities = util.pytorch_cos_sim(embedding, repeat_df['embedding'])
            indices = torch.argmax(similarities)

            if similarities[indices] > 0.85:
                return True

    return False


def group_repeated_questions(questions_df):
    # Placeholder for grouping logic
    grouped_questions = questions_df.groupby('year').apply(lambda x: x).reset_index(drop=True)

    return grouped_questions