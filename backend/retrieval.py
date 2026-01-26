from sentence_transformers import SentenceTransformer
from backend.ingestion import get_connection
import numpy, math

from typing import Tuple, List, Any, Optional, Dict
import json
from backend.llm import generate_answer

embedding_model = SentenceTransformer("BAAI/bge-base-en-v1.5")

RowType = Tuple[int, str, str, float, float]

def get_resume_sections(cursor):
    cursor.execute(
        """
        SELECT id, content
        FROM document_sections
        WHERE embedding IS NULL
        ORDER BY section_index;
        """
    )
    
    rows = cursor.fetchall()
    
    sections = []
    for row in rows:
        sections.append(
            {
                "id": row[0],
                "content": row[1],
            }
        )
    return sections

def generate_embedding(text: str): #generate vector embeddings
    embedding = embedding_model.encode(
        text,
        normalize_embeddings = True
    )
    return embedding

def update_resume_sections(cursor, section_id, embedding):
    embedding_str = "[" + ",".join (str(x) for x in embedding) + "]"
    
    cursor.execute( # update the resume_sections table and set the embedding column as the vector value
        """
        UPDATE document_sections
        SET embedding = %s::vector
        WHERE id = %s;
        """,
        (embedding_str, section_id),
    )
    
def embed_resume_sections(cursor):
    sections = get_resume_sections(cursor)
    print("Found", len(sections), "sections to embed.")
    
    for section in sections:
        print("Embeddings section:", section["id"])
        emb = generate_embedding(section["content"])
        update_resume_sections(cursor, section["id"], emb)
        
    print ("Embedding completed.")
    
def embed_query(text):
    vec = generate_embedding(text)
    return vec

def extract_jd_requirements(jd_text: str) -> Dict[str, List[str]]:
    
    system_prompt = (
        "You are an expert technical recruiter. Extract skills and requirements from the Job Description."
        "Return ONLY a JSON object with keys: 'must_have' (list of strings) and 'nice_to_have' (list of strings)."
        "No markdown formatting, just raw JSON."
    )
    user_prompt = f"Job Description:\n{jd_text}"
    
    try:
        response = generate_answer(system_prompt, user_prompt)
        response = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(response)
        return data
    except Exception as e:
        print(f"Error extracting JD requirements: {e}")
        return {"must_have": [], "nice_to_have": []}

import re

SKILLS_LIST = [
    # Programming Languages
    "python", "r", "sql", "java", "c++", "scala", "julia", "matlab", "sas",
    
    # Data Manipulation & Analysis
    "pandas", "numpy", "scipy", "dask", "polars", "vaex", "modin", 
    
    # Visualization
    "matplotlib", "seaborn", "plotly", "bokeh", "altair", "ggplot", "tableau", "power bi", "looker", "quicksight",
    
    # Machine Learning & Statistics
    "scikit-learn", "xgboost", "lightgbm", "catboost", "statsmodels", "h2o", "auto-sklearn", "tpot",
    "regression", "classification", "clustering", "time series", "forecasting", "a/b testing", "hypothesis testing",
    
    # Deep Learning (Frameworks & Architectures)
    "pytorch", "tensorflow", "keras", "mxnet", "jax", "fastai", "opencv",
    "cnn", "rnn", "lstm", "gan", "transformer", "bert", "gpt", "diffusion models",
    
    # NLP & LLM
    "nltk", "spacy", "gensim", "textblob", "hugging face", "transformers", "langchain", "llamaindex", 
    "haystack", "openai api", "anthropic", "gemini", "llama", "mistral", "rag", "retrieval augmented generation",
    "prompt engineering", "fine-tuning", "lora", "qlora",
    
    # Vector Databases & Search
    "vector database", "pgvector", "pinecone", "faiss", "weaviate", "chromadb", "milvus", "qdrant", "elasticsearch", "opensearch",
    
    # Big Data & Distributed Computing
    "spark", "pyspark", "hadoop", "hive", "kafka", "flink", "databricks", "snowflake", "bigquery", "redshift",
    
    # MLOps & Model Serving
    "mlflow", "kubeflow", "airflow", "prefect", "dbt", "wandb", "weights & biases", "bentoml", "ray", 
    "sagemaker", "vertex ai", "azure ml", "docker", "kubernetes", "git", "ci/cd",
    
    # Databases (SQL & NoSQL)
    "postgresql", "mysql", "mongodb", "cassandra", "redis", "dynamodb", "oracle", "sql server",
    
    # Cloud Platforms
    "aws", "gcp", "azure", "ibm cloud", "oracle cloud"
]

def extract_resume_entities(resume_text: str) -> Dict[str, Any]:
    # 1. Extract Skills (Keyword Matching)
    text_lower = resume_text.lower()
    found_skills = []
    
    for skill in SKILLS_LIST:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill)
            
    # 2. Extract Years of Experience
    years_pattern = r'(\d+)\+?\s*(?:years?|yrs?)'
    matches = re.findall(years_pattern, text_lower)
    
    years_experience = 0
    if matches:
        try:
        
            years = [int(m) for m in matches if int(m) < 60]
            if years:
                years_experience = max(years)
        except Exception:
            pass

    return {
        "skills": found_skills, 
        "years_experience": years_experience
    }

def _search_resume_sections_with_cursor(cursor, query_text: str, top_k: int = 3, similarity_threshold: float = 0.45, document_id: Optional[str] = None,) -> List[RowType]:
    
    query_vector = embed_query(query_text)
    embedding_str = "[" + ",".join(str(x) for x in query_vector) + "]"

    base_sql = """
        SELECT id,
               section_label,
               content,
               (embedding <=> %s::vector) AS cosine_distance,
               1 - (embedding <=> %s::vector) AS cosine_similarity
        FROM document_sections
        WHERE embedding IS NOT NULL
    """
    params: List[Any] = [embedding_str, embedding_str]

    if document_id is not None:
        base_sql += " AND document_id = %s"
        params.append(document_id)

    base_sql += """
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """
    params.extend([embedding_str, top_k])

    cursor.execute(base_sql, tuple(params))
    rows: List[RowType] = cursor.fetchall()
    
    # Filter by similarity threshold
    filtered_rows = [row for row in rows if float(row[4]) >= similarity_threshold]
    
    return filtered_rows


def search_resume_sections(query_text: str, top_k: int = 3, similarity_threshold: float = 0.45, document_id: Optional[str] = None,) -> List[RowType]:
    
    conn = get_connection()
    cursor = conn.cursor()

    try:
        rows = _search_resume_sections_with_cursor(
            cursor=cursor,
            query_text=query_text,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            document_id=document_id,
        )
        return rows
    finally:
        cursor.close()
        conn.close()
        
def results(rows):
    print("\nSearch Results:\n")
    for idx, row in enumerate(rows, start=1):
        section_id = row[0]
        section_label = row[1]
        content = row[2]
        cosine_distance = float(row[3])
        cosine_sim = float(row[4])
        
        print("Rank", idx)
        print("  Section ID:      ", section_id)
        print("  Section Label:   ", section_label)
        print("  Cosine Distance: ", round(cosine_distance, 4))
        print("  Cosine Similarity:", round(cosine_sim, 4))
        print("  Content:         ", content[:200], "...")
        print()
    
def main():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Embed all existing sections
        embed_resume_sections(cursor)
        
        query = "machine learning"
        result_rows =  _search_resume_sections_with_cursor(cursor, query, top_k=3)
        results(result_rows)

        # Commit changes
        conn.commit()
        print("All embeddings saved to database.")

    except Exception as e:
        conn.rollback()
        print("Error during embedding:", e)

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
