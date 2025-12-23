import pandas as pd
from backend.ingestion import get_connection


def get_global_ats_stats():
    
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Total jobs + open/closed breakdown
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_jobs,
                COUNT(*) FILTER (WHERE status = 'open') AS open_jobs,
                COUNT(*) FILTER (WHERE status = 'closed') AS closed_jobs
            FROM job_posts;
            """
        )
        job_row = cursor.fetchone()
        total_jobs, open_jobs, closed_jobs = job_row

        # Applications + ATS stats
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_applications,
                AVG(ats_score) AS avg_ats_score_overall,
                AVG(ats_score) FILTER (WHERE status IN ('screened', 'shortlisted')) AS avg_ats_score_screened
            FROM applications;
            """
        )
        app_row = cursor.fetchone()
        total_applications, avg_overall, avg_screened = app_row

        return {
            "total_jobs": total_jobs or 0,
            "open_jobs": open_jobs or 0,
            "closed_jobs": closed_jobs or 0,
            "total_applications": total_applications or 0,
            "avg_ats_score_overall": float(avg_overall) if avg_overall is not None else None,
            "avg_ats_score_screened": float(avg_screened) if avg_screened is not None else None,
        }

    finally:
        cursor.close()
        conn.close()


def get_applications_by_status():
    
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                status,
                COUNT(*) AS count
            FROM applications
            GROUP BY status
            ORDER BY count DESC;
            """
        )
        rows = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    if not rows:
        return pd.DataFrame(columns=["status", "count"])

    return pd.DataFrame(rows, columns=["status", "count"])


def get_department_stats():

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                jp.department,
                COUNT(DISTINCT jp.id) AS total_jobs,
                COUNT(DISTINCT jp.id) FILTER (WHERE jp.status = 'open') AS open_jobs,
                COUNT(a.id) AS total_applications,
                AVG(a.ats_score) AS avg_ats_score
            FROM job_posts jp
            LEFT JOIN applications a ON a.job_post_id = jp.id
            GROUP BY jp.department
            ORDER BY total_applications DESC;
            """
        )
        rows = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    columns = [
        "department",
        "total_jobs",
        "open_jobs",
        "total_applications",
        "avg_ats_score",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows, columns=columns)
    return df


def get_job_level_stats():
    
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                jp.id AS job_post_id,
                jp.role_title,
                jp.department,
                jp.status,
                COUNT(a.id) AS total_applications,
                AVG(a.ats_score) AS avg_ats_score
            FROM job_posts jp
            LEFT JOIN applications a ON a.job_post_id = jp.id
            GROUP BY jp.id, jp.role_title, jp.department, jp.status
            ORDER BY jp.created_at DESC;
            """
        )
        rows = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    columns = [
        "job_post_id",
        "role_title",
        "department",
        "status",
        "total_applications",
        "avg_ats_score",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows, columns=columns)
    return df


def get_applications_for_job(job_post_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                resume_document_id,
                status,
                ats_score,
                created_at
            FROM applications
            WHERE job_post_id = %s
            ORDER BY ats_score DESC NULLS LAST, created_at ASC;
            """,
            (job_post_id,),
        )
        rows = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    columns = [
        "application_id",
        "resume_document_id",
        "status",
        "ats_score",
        "created_at",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows, columns=columns)
    return df


def get_role_stats(role_pattern):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                COUNT(a.id) AS total_applications,
                AVG(a.ats_score) AS avg_score,
                MIN(a.ats_score) AS min_score,
                MAX(a.ats_score) AS max_score,
                percentile_cont(0.5) WITHIN GROUP (ORDER BY a.ats_score) AS median_score
            FROM job_posts jp
            JOIN applications a ON a.job_post_id = jp.id
            WHERE jp.role_title ILIKE %s
              AND a.ats_score IS NOT NULL;
            """,
            (role_pattern,),
        )
        row = cursor.fetchone()

        if row is None:
            return {
                "total_applications": 0,
                "avg_score": None,
                "min_score": None,
                "max_score": None,
                "median_score": None,
            }

        total_applications, avg_score, min_score, max_score, median_score = row

        return {
            "total_applications": total_applications or 0,
            "avg_score": float(avg_score) if avg_score is not None else None,
            "min_score": float(min_score) if min_score is not None else None,
            "max_score": float(max_score) if max_score is not None else None,
            "median_score": float(median_score) if median_score is not None else None,
        }

    finally:
        cursor.close()
        conn.close()
        
def get_role_score(role_pattern):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                a.ats_score
            FROM applications a
            JOIN job_posts jp ON jp.id = a.job_post_id
            WHERE jp.role_title ILIKE %s
              AND a.ats_score IS NOT NULL
            ORDER BY a.ats_score;
            """,
            (role_pattern,),
        )
        rows = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    if not rows:
        return pd.DataFrame(columns=["ats_score"])

    scores = [r[0] for r in rows]
    df = pd.DataFrame({"ats_score": scores})
    return df

def get_missing_skills(role_pattern, limit=20):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                LOWER(TRIM(skill)) AS skill,
                COUNT(*) AS missing_count
            FROM applications a
            JOIN job_posts jp ON jp.id = a.job_post_id
            CROSS JOIN LATERAL jsonb_array_elements_text(a.missing_skills) AS skill
            WHERE jp.role_title ILIKE %s
              AND a.missing_skills IS NOT NULL
            GROUP BY LOWER(TRIM(skill))
            ORDER BY missing_count DESC
            LIMIT %s;
            """,
            (role_pattern, limit),
        )
        rows = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    columns = ["skill", "missing_count"]

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows, columns=columns)
    return df