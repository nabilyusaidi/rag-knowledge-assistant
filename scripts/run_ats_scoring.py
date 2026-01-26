
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.ingestion import get_connection
from backend.ats import evaluate_application
import time

def run_scoring(batch_size=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    print("Fetching pending applications...")
    
    try:
        # Fetch status='new' or where score IS NULL
        cursor.execute("""
            SELECT id 
            FROM applications 
            WHERE status = 'new' OR ats_score IS NULL
        """)
        app_ids = [row[0] for row in cursor.fetchall()]
        
        print(f"Found {len(app_ids)} applications to score.")
        
        if not app_ids:
            return

        count = 0
        for app_id in app_ids:
            if batch_size and count >= batch_size:
                break
                
            print(f"Scoring {count+1}/{len(app_ids)}: Application {app_id}")
            try:
                evaluate_application(str(app_id))
                count += 1
                # Optional: Sleep to prevent rate limits depending on LLM usage
                # time.sleep(0.5) 
            except Exception as e:
                print(f"Failed to score {app_id}: {e}")
                
        print(f"Completed scoring {count} applications.")
        
    except Exception as e:
        print(f"Error fetching applications: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # Optional: pass limit arg
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Limit number of apps to score", default=None)
    args = parser.parse_args()
    
    run_scoring(args.limit)
