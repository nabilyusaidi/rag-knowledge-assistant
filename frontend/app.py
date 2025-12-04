import streamlit as st

st.set_page_config(
    page_title="FYP 2.0 – RAG Demo",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 FYP 2.0 – Intelligent Document Analysis System")

st.markdown(
    """
Use the sidebar to:
- 📄 **Upload & ingest** resumes into the database  
- ❓ **Ask questions** over all ingested resumes or a specific one  

This is a thin Streamlit UI on top of the backend RAG system (PostgreSQL + pgvector, BGE embeddings, Zephyr LLM).
"""
)
