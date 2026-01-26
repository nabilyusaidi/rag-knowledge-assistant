import streamlit as st
import pandas as pd
from backend.ats import generate_ai_explanation
from backend.analytics import (
    get_global_ats_stats,
    get_applications_by_status,
    get_department_stats,
    get_job_level_stats,
    get_applications_for_job,
    get_role_stats,
    get_role_score,
    get_missing_skills,
    get_missing_skills_for_job,
    get_application_details
)


def main():
    st.title("ATS – Analytics Dashboard")

    # ===== GLOBAL STATS =====
    st.header("Overview")

    stats = get_global_ats_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Jobs Posts", stats["total_jobs"])
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
            data=df_status.set_index("status")["count"],
            horizontal=True
        )

    st.write("---")

    # ===== DEPARTMENT STATS =====
    st.subheader("Per-Department Stats")

    df_dept = get_department_stats()
    if df_dept.empty:
        st.info("No job posts found.")
    else:
        st.dataframe(df_dept, use_container_width=True)
        st.caption("Applications by Department")
        st.bar_chart(
            data=df_dept.set_index("department")["total_applications"],
            horizontal=True
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
            available_cols = df_apps.columns.tolist()
            display_cols = ["application_id", "resume_name", "status", "ats_score", "created_at"]
            final_cols = [c for c in display_cols if c in available_cols]
            
            # Sort by ATS Score descending
            if "ats_score" in df_apps.columns:
                df_apps = df_apps.sort_values(by="ats_score", ascending=False)

            st.dataframe(df_apps[final_cols], use_container_width=True)

            # small score distribution chart
            # Score Distribution Histogram
            if "ats_score" in df_apps.columns and df_apps["ats_score"].notnull().any():
                st.caption("ATS Score Distribution")
                
                # Create bins for better visualization
                bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 101]
                labels = ['0-10', '11-20', '21-30', '31-40', '41-50', '51-60', '61-70', '71-80', '81-90', '91-100']
                
                valid_scores = df_apps.dropna(subset=["ats_score"])["ats_score"].astype(float)
                
                score_cats = pd.cut(valid_scores, bins=bins, labels=labels, right=False)
                dist_data = score_cats.value_counts().sort_index()
                
                st.bar_chart(dist_data)

            # Candidate Gap Analysis Section
            st.markdown("### Candidate Analysis")
            st.caption("Select a candidate to view their assessment summary and detailed gap analysis.")

            candidate_options = df_apps[["application_id", "resume_name", "ats_score"]].to_dict('records')
            
            selected_app_id = st.selectbox(
                "Select Candidate",
                options=[c["application_id"] for c in candidate_options],
                format_func=lambda x: next((f"{c['resume_name']} (Score: {c['ats_score']})" for c in candidate_options if c["application_id"] == x), x)
            )

            if selected_app_id:
                details = get_application_details(selected_app_id)
                
                if details:
                    score = details["ats_score"]
                    breakdown = details["score_breakdown"]
                    resume_name = details["resume_name"]
                     
                    # Overall fit calculation
                    if score >= 70:
                        fit_label = "Strong Fit"
                        fit_delta = "High Match"
                        fit_delta_color = "normal" 
                    elif score >= 50:
                        fit_label = "Partial Fit"
                        fit_delta = "Medium Match"
                        fit_delta_color = "off"
                    else:
                        fit_label = "Low Fit"
                        fit_delta = "Low Match"
                        fit_delta_color = "inverse"

                    # Header Section
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.subheader(f"{resume_name}")
                    with c2:
                        st.metric("ATS Score", f"{score:.0f}/100", delta=fit_label, delta_color=fit_delta_color)

                    score_details = breakdown.get("score_details", {})
                    explanation = breakdown.get("explanation", {})
                    
                    # HR Takeaway (Prominent)
                    reasoning = explanation.get("reasoning", "No assessment generated.")
                    
                    if reasoning == "Click 'Generate Explanation' to view AI analysis." or reasoning == "No assessment generated.":
                        st.warning("AI Analysis not yet generated.")
                        if st.button("Generate AI Explanation"):
                             with st.spinner("Generating explanation..."):
                                  generate_ai_explanation(selected_app_id)
                                  st.success("Generated!")
                                  st.rerun()
                    else:
                        st.info(f"**HR Assessment**: {reasoning}")
                    
                    st.divider()

                    # Two-column layout for analysis
                    col_gaps, col_strengths = st.columns(2)
                    
                    with col_gaps:
                        st.markdown("#### ⚠️ Gaps & Risks")
                        
                        # Critical Gaps
                        missing_must = score_details.get("missing_must", [])
                        st.markdown("**Critical Gaps** (Immediate Mismatch)")
                        if missing_must:
                            for gap in missing_must:
                                st.markdown(f"- {gap}")
                            st.caption("These skills are required for the role.")
                        else:
                            st.markdown("*No critical gaps identified*")
                        
                        st.write("") # spacer

                        # Moderate Gaps
                        missing_nice = score_details.get("missing_nice", [])
                        st.markdown("**Moderate Gaps** (Trainable)")
                        if missing_nice:
                            for gap in missing_nice:
                                st.markdown(f"- {gap}")
                            st.caption("Can likely be addressed with onboarding/training.")
                        else:
                             st.markdown("*No moderate gaps identified*")

                    with col_strengths:
                        st.markdown("#### ✅ Strengths & Assets")
                        
                        matched_must = score_details.get("matched_must", [])
                        matched_nice = score_details.get("matched_nice", [])
                        matches = list(set(matched_must + matched_nice))
                        
                        if matches:
                            for match in matches:
                                st.markdown(f"- {match}")
                        else:
                            st.markdown("*(No explicit skill matches found)*")

                else:
                    st.error("Could not load details for this application.")
                
        st.write("---")





def _format_job_label(df_jobs, job_post_id):
    row = df_jobs.loc[df_jobs["job_post_id"] == job_post_id].iloc[0]
    role = row["role_title"]
    dept = row["department"]
    status = row["status"]
    return f"{role} ({status})"


if __name__ == "__main__":
    main()
