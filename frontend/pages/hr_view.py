import streamlit as st
import pandas as pd

from backend.ingestion import get_connection 


def fetch_job_posts():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                role_title,
                department,
                seniority,
                location,
                status,
                created_at
            FROM job_posts
            ORDER BY created_at DESC;
            """
        )
        rows = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    columns = [
        "id",
        "role_title",
        "department",
        "seniority",
        "location",
        "status",
        "created_at",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(rows, columns=columns)


def main():
    st.title("ATS – Job Posts Overview")

    st.write("This page shows all job posts that HR has created in the system.")

    df = fetch_job_posts()

    if df.empty:
        st.info("No job posts found. Go to the HR JD page to create one.")
        return

    st.subheader("Job Posts")
    st.dataframe(df, use_container_width=True)

    # Optional: quick detail view
    selected_id = st.selectbox(
        "Select a job_post to view details",
        df["id"].tolist(),
        format_func=lambda x: f"{x} – {df.loc[df['id'] == x, 'role_title'].values[0]}",
    )

    if selected_id:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    role_title,
                    department,
                    seniority,
                    location,
                    status,
                    raw_job_description_text
                FROM job_posts
                WHERE id = %s;
                """,
                (selected_id,),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if row:
            (
                role_title,
                department,
                seniority,
                location,
                status,
                raw_jd_text,
            ) = row

            st.markdown("---")
            st.subheader("Selected Job Post Details")
            st.write(f"**Role Title:** {role_title}")
            st.write(f"**Department:** {department}")
            st.write(f"**Seniority:** {seniority}")
            st.write(f"**Location:** {location}")
            st.write(f"**Status:** {status}")

            if raw_jd_text:
                st.markdown("**Job Description:**")
                st.text_area(
                    "Raw JD text",
                    value=raw_jd_text,
                    height=250,
                    disabled=True,
                )


if __name__ == "__main__":
    main()
