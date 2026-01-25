import sys
import os

from typing import List, Tuple, Optional

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


from backend.ingestion import get_connection
from backend.rag_pipeline import answer_query


def list_documents() -> List[Tuple[str, str]]:
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, title
            FROM documents
            ORDER BY title;
            """
        )
        rows = cursor.fetchall()
        return [(str(r[0]), r[1]) for r in rows]
    finally:
        cursor.close()
        conn.close()

# ----------------- Streamlit UI -----------------

st.title("❓ Ask Questions about Resumes")

st.markdown(
    "You can either search across **all ingested resumes** or restrict the search "
    "to a specific document."
    "\n\nLLM Model: Gemini 3 Flash Preview"
)

docs = list_documents()

options = ["🔍 All documents"]
doc_id_map = {}  # label -> id

for doc_id, title in docs:
    label = f"{title} ({doc_id[:8]})"
    options.append(label)
    doc_id_map[label] = doc_id

selected_option = st.selectbox("Search within:", options)

if selected_option == "🔍 All documents":
    selected_doc_id: Optional[str] = None
else:
    selected_doc_id = doc_id_map[selected_option]

with st.form(key="qa_form"):
    # Question input
    question = st.text_area(
        "Your question",
        placeholder="e.g. What machine learning projects has this candidate worked on?",
    )

    top_k = st.slider("Number of sections to retrieve (top_k)", min_value=1, max_value=10, value=3)

    # Ask button
    submitted = st.form_submit_button("Ask")

if submitted:
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Thinking..."):
            answer, rows = answer_query(
                query=question,
                top_k=top_k,
                document_id=selected_doc_id,
            )

        st.subheader("Answer")
        st.write(answer)

        #Show retrieved contexts
        st.subheader("Retrieved Contexts")
        if not rows:
            st.write("No matching sections were retrieved.")
        else:
            for i, row in enumerate(rows, start=1):
                section_id, section_label, content, dist, sim = row
                with st.expander(
                    f"Context {i}: {section_label} (sim={sim:.3f}, id={section_id})"
                ):
                    st.write(content)
                    