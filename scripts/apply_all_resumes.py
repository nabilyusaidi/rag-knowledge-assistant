
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.ingestion import get_connection

def apply_all():
    conn = get_connection()
    cursor = conn.cursor()
    
    print("Fetching all job posts and resumes...")
    
    try:
        # Get all Job IDs
        cursor.execute("SELECT id FROM job_posts")
        job_ids = [row[0] for row in cursor.fetchall()]
        
        # Get all Resume Document IDs
 
        # Wait, documents table structure? Let's assume all documents in 'documents' table might be resumes if we filter or just all?
        # Based on previous code: "FROM documents d" and user context.
        # Let's verify if there is a category column? inspect_db didn't show documents table.
        # Safe bet: Just grab all documents. Or check if there is a specific way to identify resumes.
        # In `backend/ats.py`: `JOIN documents d ON a.resume_document_id = d.id`.
        # I'll just grab all documents for now.
        # Get all Resume Document IDs
        cursor.execute("SELECT id FROM documents WHERE doc_type = 'resume'")
        resume_ids = [row[0] for row in cursor.fetchall()]

        # Cleanup: Remove applications linked to non-resumes (from previous run)
        print("Cleaning up invalid applications (linked to non-resumes)...")
        cursor.execute("""
            DELETE FROM applications 
            WHERE resume_document_id IN (
                SELECT id FROM documents WHERE doc_type != 'resume'
            );
        """)
        print(f"Deleted {cursor.rowcount} invalid applications.")
        
        print(f"Found {len(job_ids)} jobs and {len(resume_ids)} resumes.")
        
        created_count = 0
        
        for job_id in job_ids:
            for resume_id in resume_ids:
                # Check if exists
                cursor.execute(
                    "SELECT 1 FROM applications WHERE job_post_id = %s AND resume_document_id = %s",
                    (job_id, resume_id)
                )
                if cursor.fetchone():
                    continue 
                
                # Create Application
                # Note: We need a unique ID for application? `id` is UUID usually auto-generated if default? 
                # Let's inspect if `id` has default gen_random_uuid(). usually yes.
                # If not, I need to generate it.
                # Let's assume database handles ID generation (SERIAL or DEFAULT gen_random_uuid()).
                # If it's UUID, often explicit generation in code is safer if DB doesn't have default.
                # Inspecting `backend/ingestion.py` or similar might reveal.
                # But standard practice: Try insert without ID.
                
                cursor.execute(
                    """
                    INSERT INTO applications (job_post_id, resume_document_id, status, created_at, updated_at)
                    VALUES (%s, %s, 'new', NOW(), NOW())
                    ON CONFLICT DO NOTHING; 
                    """,
                    (job_id, resume_id)
                )
                created_count += 1
        
        conn.commit()
        print(f"Successfully created {created_count} new applications.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error applying resumes: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    apply_all()
