from sentence_transformers import SentenceTransformer
from backend.ingestion import get_connection
import numpy, math

embedding_model = SentenceTransformer("BAAI/bge-base-en-v1.5")

def get_resume_sections(cursor):
    cursor.execute(
        """
        SELECT id, content
        FROM resume_sections
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
        UPDATE resume_sections
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

def search_resume_sections(cursor, query_text, top_k=3):
    query_vector = embed_query(query_text) #turns query_text into a vector using the embed_query function
    
    embedding_str = "[" + ",".join(str(x) for x in query_vector) + "]" #convert the existing vector into a pgvector format string
    
    
    cursor.execute( # use cosine distance in postgres
        """
        SELECT id, section_label, content, (embedding <=> %s::vector) AS cosine_distance,
            1 - (embedding <=> %s::vector) AS cosine_similarity
        FROM resume_sections
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """,
        (embedding_str, embedding_str, embedding_str, top_k)
    )
    rows = cursor.fetchall()
    return rows

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
        result_rows = search_resume_sections(cursor, query, top_k=3)
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
