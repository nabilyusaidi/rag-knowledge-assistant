from typing import Optional, Tuple

from psycopg2.extras import Json
from backend.ingestion import get_connection, insert_document, insert_sections, clean_text
from backend.retrieval import extract_jd_requirements, extract_resume_entities, get_connection
from backend.ingestion import read_pdf_text, clean_text
import json
import os
from backend.llm import generate_answer

import re
from backend.retrieval import SKILLS_LIST

def calculate_ats_score(resume_data: dict, jd_data: dict) -> dict:

    resume_skills = set(resume_data.get("skills", []))
    
    # Helper to extract standard skills from verbose JD text lists
    def extract_skills_from_text_list(text_list):
        found = set()
        combined_text = " ".join(str(x) for x in text_list).lower()
        for skill in SKILLS_LIST:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, combined_text):
                found.add(skill)
        return found
    
    must_have_raw = jd_data.get("must_have", [])
    must_have_skills = extract_skills_from_text_list(must_have_raw)
    
    nice_to_have_raw = jd_data.get("nice_to_have", [])
    nice_to_have_skills = extract_skills_from_text_list(nice_to_have_raw)
    
    if not must_have_skills and not nice_to_have_skills:
        pass

    # Calculate Matches
    matched_must = must_have_skills.intersection(resume_skills)
    missing_must = must_have_skills - matched_must
    
    matched_nice = nice_to_have_skills.intersection(resume_skills)
    missing_nice = nice_to_have_skills - matched_nice
    
    # Compute Score Formula
    # Weight: Must Have = 70%, Nice to Have = 30%
    
    # Denominators
    len_must = len(must_have_skills)
    len_nice = len(nice_to_have_skills)
    
    score_must = (len(matched_must) / len_must) * 70 if len_must > 0 else 70 # Give full points if no requirement
    score_nice = (len(matched_nice) / len_nice) * 30 if len_nice > 0 else 30 # Give full points if no requirement

    # Adjust weighting if one category is empty
    if len_must == 0 and len_nice == 0:
        final_score = 0 # No skills to match against in JD
    elif len_must == 0:
        final_score = (len(matched_nice) / len_nice) * 100
    elif len_nice == 0:
        final_score = (len(matched_must) / len_must) * 100
    else:
        final_score = score_must + score_nice
        
    return {
        "score": int(final_score),
        "matched_must": list(matched_must),
        "missing_must": list(missing_must),
        "matched_nice": list(matched_nice),
        "missing_nice": list(missing_nice)
    }

def generate_ats_explanation(score_data: dict, resume_text: str, jd_text: str) -> dict:
    system_prompt = (
        "You are an expert ATS auditor. Explain the deterministic scoring results to a hiring manager."
        "Focus on GAPS and STRENGTHS. Be concise."
        "Return ONLY a JSON object with keys: 'reasoning' (string) and 'improvements' (string)."
    )
    
    user_prompt = (
        f"Score Data: {json.dumps(score_data, indent=2)}\n\n"
        "Draft a reasoning summary explaining why they got this score, and what they can do to improve."
    )
    
    try:
        response = generate_answer(system_prompt, user_prompt)
        response = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(response)
        return data
    except Exception as e:
        print(f"Error generating explanation: {e}")
        return {"reasoning": "Could not generate explanation.", "improvements": "N/A"}

def evaluate_application(application_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get Application Data (JD text + Resume path)
        cursor.execute(
            """
            SELECT 
                a.job_post_id, 
                a.resume_document_id,
                jp.raw_job_description_text,
                jp.requirements, -- Cached JD requirements
                d.source_path
            FROM applications a
            JOIN job_posts jp ON a.job_post_id = jp.id
            JOIN documents d ON a.resume_document_id = d.id
            WHERE a.id = %s
            """,
            (application_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            print(f"Application {application_id} not found.")
            return

        job_post_id, resume_id, jd_text, cached_requirements, resume_path = row
        
        # Extract JD Requirements
        if not cached_requirements:
            print("Extracting JD requirements...")
            jd_data = extract_jd_requirements(jd_text)
            
            cursor.execute(
                "UPDATE job_posts SET requirements = %s WHERE id = %s",
                (json.dumps(jd_data), job_post_id)
            )
            conn.commit()
        else:
            
            jd_data = cached_requirements if isinstance(cached_requirements, dict) else json.loads(cached_requirements)

        # Extract Resume Data
        if os.path.exists(resume_path):
             raw_resume = read_pdf_text(resume_path)
             cleaned_resume = clean_text(raw_resume)
        else:
              cursor.execute("SELECT content FROM document_sections WHERE document_id = %s", (resume_id,))
              sec_rows = cursor.fetchall()
              cleaned_resume = "\n".join([r[0] for r in sec_rows])
        
        print("Extracting Resume entities...")
        resume_data = extract_resume_entities(cleaned_resume)
        
        #Calculate Score (Deterministic)
        print("Calculating deterministic score...")
        score_result = calculate_ats_score(resume_data, jd_data)
        
        # Explanation is now on-demand
        explanation = {"reasoning": "Click 'Generate Explanation' to view AI analysis.", "improvements": "N/A"}
        
        full_breakdown = { # save for reference
            "resume_data": resume_data,
            "jd_data": jd_data,
            "score_details": score_result,
            "explanation": explanation
        }
        
        cursor.execute(
            """
            UPDATE applications
            SET 
                ats_score = %s,
                status = 'screened',
                metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb,
                missing_skills = %s
            WHERE id = %s
            """,
            (
                score_result["score"],
                json.dumps({"score_breakdown": full_breakdown}),
                json.dumps(score_result["missing_must"]),
                application_id
            )
        )
        conn.commit()
        print(f"Scored Application {application_id}: {score_result['score']}/100")
        
    except Exception as e:
        conn.rollback()
        print(f"Error scoring application {application_id}: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def generate_ai_explanation(application_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Fetch necessary data
        cursor.execute(
            """
            SELECT 
                jp.raw_job_description_text,
                d.source_path,
                a.resume_document_id,
                a.metadata->'score_breakdown'->>'score_details' as score_details,
                a.metadata->'score_breakdown'->>'resume_data' as resume_data,
                a.metadata->'score_breakdown' as full_breakdown
            FROM applications a
            JOIN job_posts jp ON a.job_post_id = jp.id
            JOIN documents d ON a.resume_document_id = d.id
            WHERE a.id = %s
            """,
            (application_id,)
        )
        row = cursor.fetchone()
        if not row:
            return {"error": "Application not found"}
            
        jd_text, resume_path, resume_id, score_details_json, resume_data_json, full_breakdown_json = row
        
        # Parse JSONs
        score_data = json.loads(score_details_json) if isinstance(score_details_json, str) else score_details_json
        full_breakdown = json.loads(full_breakdown_json) if isinstance(full_breakdown_json, str) else full_breakdown_json
        
        # Extract Resume Text
        if os.path.exists(resume_path):
             raw_resume = read_pdf_text(resume_path)
             cleaned_resume = clean_text(raw_resume)
        else:
              cursor.execute("SELECT content FROM document_sections WHERE document_id = %s", (resume_id,))
              sec_rows = cursor.fetchall()
              cleaned_resume = "\n".join([r[0] for r in sec_rows])
              
        # Generate Explanation
        explanation = generate_ats_explanation(score_data, cleaned_resume, jd_text)
        
        # Update DB
        full_breakdown["explanation"] = explanation
        
        cursor.execute(
            """
            UPDATE applications
            SET metadata = metadata || %s::jsonb
            WHERE id = %s
            """,
            (json.dumps({"score_breakdown": full_breakdown}), application_id)
        )
        conn.commit()
        return explanation
        
    except Exception as e:
        conn.rollback()
        print(f"Error generating explanation: {e}")
        return {"reasoning": f"Error: {str(e)}", "improvements": "N/A"}
    finally:
        cursor.close()
        conn.close()