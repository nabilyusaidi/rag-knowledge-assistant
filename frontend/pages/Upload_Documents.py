import sys
import os
import tempfile

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.ingestion import (
    main as ingest_pdf,
    read_pdf_text,
    clean_text,
    extract_sections,
)

st.title("📄 Upload & Ingest Document")

st.markdown(
    "Upload a **PDF resume** to ingest it into the RAG system. "
    "The backend will extract sections, store them in PostgreSQL + pgvector, "
    "and compute embeddings (once you run your embedding pipeline)."
)

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    st.write(f"**File name:** `{uploaded_file.name}`")

    if st.button("Ingest document"):
        # 1. Save uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        try:
            with st.spinner("Ingesting document into database..."):
                # 2. Run your existing ingestion pipeline
                #    This will:
                #      - insert into `documents`
                #      - read & clean text
                #      - extract sections
                #      - insert into `resume_sections`
                ingest_pdf(tmp_path, original_filename=uploaded_file.name)

            # 3. Compute section & token counts for display
            raw_text = read_pdf_text(tmp_path)
            cleaned = clean_text(raw_text)
            sections = extract_sections(cleaned)

            section_count = len(sections)
            # crude token count; you can swap in a tokenizer if you want
            token_count = len(cleaned.split())

            st.success("Ingestion completed successfully ✅")

            # 4. Show metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Sections", section_count)
            with col2:
                st.metric("Approx. tokens", token_count)

            # 5. Leave room for future detail
            with st.expander("View more details"):
                st.write(
                    "Section labels available:"
                )
                preview_labels = [s.get("label", "unknown") for s in sections[:5]]
                st.write(preview_labels)

        except Exception as e:
            st.error(f"Error during ingestion: {e}")

        finally:
            # clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
