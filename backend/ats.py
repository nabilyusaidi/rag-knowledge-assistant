from typing import Optional, Tuple

from psycopg2.extras import Json
from backend.ingestion import get_connection, insert_document, insert_sections, clean_text

def create_jd_sections(raw_text: str):
    cleaned = clean_text(raw_text)
    
    sections = []
    
    if cleaned.strip():
        sections.append(
            {
                "label": "job_description",
                "index": 0,
                "content": cleaned,
            }
        )
    
    return sections

def create_job_posts(
    role_title: str,
    department: Optional[str],
    seniority: Optional[str],
    location: Optional[str],
    raw_JD_text: str,
) -> Tuple[int, int]:
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute( #insert job_posts row
            """
            INSERT INTO job_posts (role_title, department, seniority, location, raw_job_description_text)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (role_title, department, seniority, location, raw_JD_text),
        )
        
        job_post_id = cursor.fetchone()[0]
        print("Inserted job_post ID:", job_post_id)
        
        
        title = f"JD - {role_title}" #insert jd into documents table as job_description
        jd_document_id = insert_document(
            cursor=cursor,
            title=title,
            source_path="",
            doc_type="job_description",
        )
        print("Inserted JD document ID:", jd_document_id)
        
        #create jd sections and insert into document_sections
        jd_sections = create_jd_sections(raw_JD_text)
        print("JD has", len(jd_sections), "sections.")
        
        insert_sections(
            cursor=cursor,
            document_id=jd_document_id,
            sections=jd_sections,
            doc_type="job_description",
        )
        
        #link the job_posts with documents using document id
        cursor.execute(
            """
            UPDATE job_posts
            SET document_id = %s
            WHERE id = %s;
            """,
            (jd_document_id, job_post_id),
        )

        conn.commit()
        print("Job post + JD ingestion completed.")

        return job_post_id, jd_document_id
    
    except Exception as e:
        conn.rollback()
        print("Error during job post creation:", e)
        raise

    finally:
        cursor.close()
        conn.close()
        
def create_applications(job_post_id: int, resume_document_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO applications (job_post_id, resume_document_id,status)
            VALUES(%s, %s, 'applied')
            RETURNING id;
            """,
            (job_post_id, resume_document_id)
        )
        application_id = cursor.fetchone()[0]
        conn.commit()
        
        print("Inserted Application ID:", application_id)
        return application_id
    
    except Exception as e:
        conn.rollback()
        print("Error during application creation:", e)
        raise

    finally:
        cursor.close()
        conn.close()
        
if __name__ == "__main__":
    sample_role_title = "Junior ML Engineer"
    sample_department = "Engineering"
    sample_seniority = "Junior"
    sample_location = "Kuala Lumpur"

    sample_jd_text = """
    We are looking for a Junior Machine Learning Engineer to join our Engineering team in Kuala Lumpur.

    Responsibilities:
    - Build and maintain ML models for production.
    - Collaborate with Data Scientists and Software Engineers.
    - Deploy models using modern MLOps practices.

    Requirements:
    - Strong Python skills.
    - Experience with machine learning libraries such as scikit-learn, PyTorch, or TensorFlow.
    - Understanding of SQL and data pipelines.
    """

    job_post_id, jd_document_id = create_job_posts(
        role_title = sample_role_title,
        department = sample_department,
        seniority = sample_seniority,
        location = sample_location,
        raw_JD_text = sample_jd_text,
    )

    print("Created job_post_id:", job_post_id)
    print("Created jd_document_id:", jd_document_id)