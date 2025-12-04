import sys
import os

from typing import List, Tuple, Optional

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


from backend.ingestion import get_connection
from backend.retrieval import embed_query
from backend.llm import generate_answer

from backend.rag_pipeline import format_context, build_user_prompt, get_system_prompt


RowType = Tuple[int, str, str, float, float]  # id, section_label, content, dist, sim


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
        # rows: List[Tuple[uuid, title]]
        return [(str(r[0]), r[1]) for r in rows]
    finally:
        cursor.close()
        conn.close()


def search_sections(
    query_text: str,
    top_k: int = 3,
    document_id: Optional[str] = None,
) -> List[RowType]:
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query_vector = embed_query(query_text)
        embedding_str = "[" + ",".join(str(x) for x in query_vector) + "]"

        base_sql = """
            SELECT id, section_label, content,
                   (embedding <=> %s::vector) AS cosine_distance,
                   1 - (embedding <=> %s::vector) AS cosine_similarity
            FROM resume_sections
            WHERE embedding IS NOT NULL
        """
        params = [embedding_str, embedding_str]

        if document_id is not None:
            base_sql += " AND document_id = %s"
            params.append(document_id)

        base_sql += """
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """

        params.extend([embedding_str, top_k])

        cursor.execute(base_sql, tuple(params))
        rows = cursor.fetchall()
        return rows

    finally:
        cursor.close()
        conn.close()


def answer_query_streamlit(
    query: str,
    top_k: int = 3,
    document_id: Optional[str] = None,
) -> Tuple[str, List[RowType]]:
    
    rows = search_sections(query_text=query, top_k=top_k, document_id=document_id)
    context_text = format_context(rows)
    system_prompt = get_system_prompt()
    user_prompt = build_user_prompt(query, context_text)
    answer = generate_answer(system_prompt, user_prompt)
    return answer, rows


# ----------------- Streamlit UI -----------------

st.title("❓ Ask Questions about Resumes")

st.markdown(
    "You can either search across **all ingested resumes** or restrict the search "
    "to a specific document."
)

# Document selection
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

#Question input
question = st.text_area(
    "Your question",
    placeholder="e.g. What machine learning projects has this candidate worked on?",
)

top_k = st.slider("Number of sections to retrieve (top_k)", min_value=1, max_value=10, value=3)

# Ask button
if st.button("Ask"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Thinking..."):
            answer, rows = answer_query_streamlit(
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
                    