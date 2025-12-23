import streamlit as st
import pandas as pd

from backend.analytics import (
    get_global_ats_stats,
    get_applications_by_status,
    get_department_stats,
    get_job_level_stats,
    get_applications_for_job,
    get_role_stats,
    get_role_score,
    get_missing_skills
)


def main():
    st.title("ATS – Analytics Dashboard")

    # ===== GLOBAL STATS =====
    st.header("Overview")

    stats = get_global_ats_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Jobs", stats["total_jobs"])
    with col2:
        st.metric("Open Jobs", stats["open_jobs"])
    with col3:
        st.metric("Total Applications", stats["total_applications"])
    with col4:
        avg_score = stats["avg_ats_score_overall"]
        st.metric("Avg ATS Score", f"{avg_score:.2f}" if avg_score is not None else "N/A")

    st.write("---")

    # ===== APPLICATIONS BY STATUS =====
    st.subheader("Applications by Status")

    df_status = get_applications_by_status()
    if df_status.empty:
        st.info("No applications yet.")
    else:
        st.dataframe(df_status, use_container_width=True)
        st.bar_chart(
            data=df_status.set_index("status")["count"]
        )

    st.write("---")

    # ===== DEPARTMENT STATS =====
    st.subheader("Per-Department Stats")

    df_dept = get_department_stats()
    if df_dept.empty:
        st.info("No job posts found.")
    else:
        st.dataframe(df_dept, use_container_width=True)

        # Quick visualization: applications by department
        st.caption("Applications by Department")
        st.bar_chart(
            data=df_dept.set_index("department")["total_applications"]
        )

    st.write("---")

    # ===== PER-JOB STATS + DETAIL VIEW =====
    st.subheader("Per-Job Stats")

    df_jobs = get_job_level_stats()
    if df_jobs.empty:
        st.info("No job posts yet.")
        return

    st.dataframe(df_jobs, use_container_width=True)

    # Detailed view for selected job_post
    job_ids = df_jobs["job_post_id"].tolist()

    selected_job_id = st.selectbox(
        "Select a Job to view applications",
        job_ids,
        format_func=lambda x: _format_job_label(df_jobs, x),
    )

    if selected_job_id:
        st.markdown("### Applications for selected job")

        df_apps = get_applications_for_job(selected_job_id)

        if df_apps.empty:
            st.info("No applications for this job yet.")
        else:
            st.dataframe(df_apps, use_container_width=True)

            # small score distribution chart
            if df_apps["ats_score"].notnull().any():
                st.caption("ATS Score Distribution for this Job")
                st.bar_chart(
                    data=df_apps.dropna(subset=["ats_score"]).set_index("application_id")["ats_score"]
                )
                
        st.write("---")

    st.header("Role-Specific ATS Analytics")

    # Define roles
    roles = [
        ("AI Engineer", "%AI Engineer%"),
        ("Data Scientist", "%Data Scientist%"),
    ]

    for role_label, role_pattern in roles:
        st.subheader(role_label)

        # ===== STATS FOR THIS ROLE =====
        stats = get_role_stats(role_pattern)

        if stats["total_applications"] == 0:
            st.info("No applications found for this role (including its variants).")
            continue

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Applications", stats["total_applications"])
        with col2:
            st.metric(
                "Avg ATS Score",
                f"{stats['avg_score']:.2f}" if stats["avg_score"] is not None else "N/A",
            )
        with col3:
            st.metric(
                "Median ATS Score",
                f"{stats['median_score']:.2f}" if stats["median_score"] is not None else "N/A",
            )
        with col4:
            st.metric(
                "Min ATS Score",
                f"{stats['min_score']:.2f}" if stats["min_score"] is not None else "N/A",
            )
        with col5:
            st.metric(
                "Max ATS Score",
                f"{stats['max_score']:.2f}" if stats["max_score"] is not None else "N/A",
            )

        # ===== SCORE DISTRIBUTION (HISTOGRAM-LIKE) =====
        df_scores = get_role_score(role_pattern)

        if not df_scores.empty:
            st.caption("ATS Score Distribution")

            
            df_scores["bin"] = pd.cut(
                df_scores["ats_score"],
                bins=[0, 20, 40, 60, 80, 100],
                include_lowest=True,
                right=True,
            )

            df_hist = (
                df_scores.groupby("bin")
                .size()
                .reset_index(name="count")
            )

            # Make bin labels a bit nicer
            df_hist["bin_label"] = df_hist["bin"].astype(str)

            st.bar_chart(
                data=df_hist.set_index("bin_label")["count"]
            )
        else:
            st.info("No ATS scores recorded yet for this role.")

        # ===== TOP MISSING SKILLS FOR THIS ROLE =====
        st.caption("Top Missing Skills for this Role")

        df_missing = get_missing_skills(role_pattern, limit=15)

        if df_missing.empty:
            st.info("No missing skills data yet. Make sure ATS scoring populates the 'missing_skills' column.")
        else:
            st.dataframe(df_missing, use_container_width=True)
            st.bar_chart(
                data=df_missing.set_index("skill")["missing_count"]
            )

        st.write("")  # small spacing between roles



def _format_job_label(df_jobs, job_post_id):
    row = df_jobs.loc[df_jobs["job_post_id"] == job_post_id].iloc[0]
    role = row["role_title"]
    dept = row["department"]
    status = row["status"]
    return f"{job_post_id} – {role} [{dept}] ({status})"


if __name__ == "__main__":
    main()
