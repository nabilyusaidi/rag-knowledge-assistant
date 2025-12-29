import streamlit as st
from backend.ats import create_job_posts

def main():
    st.title("Create Job Post (HR)")

    st.write("Fill in the job information and paste the full job description text.")

    with st.form("create_job_post_form"):
        role_title = st.text_input("Role Title", "")
        department = st.text_input("Department", "")
        seniority = st.text_input("Seniority (e.g. Junior, Mid, Senior)", "")
        location = st.text_input("Location", "")

        raw_JD_text = st.text_area(
            "Job Description (paste full JD here)",
            height=300,
            placeholder="Paste the job description that HR prepared...",
        )

        submitted = st.form_submit_button("Create Job Post")

    if submitted:
        if role_title.strip() == "" or raw_JD_text.strip() == "":
            st.error("Role Title and Job Description are required.")
        else:
            try:
                job_post_id, jd_document_id = create_job_posts(
                    role_title=role_title.strip(),
                    department=department.strip() or None,
                    seniority=seniority.strip() or None,
                    location=location.strip() or None,
                    raw_JD_text=raw_JD_text,
                )

                st.success("Job post created successfully.")
                st.write(f"**job_post_id:** {job_post_id}")
                st.write(f"**jd_document_id:** {jd_document_id}")

            except Exception as e:
                st.error(f"Error creating job post: {e}")
                st.exception(e)

if __name__ == "__main__":
    main()
