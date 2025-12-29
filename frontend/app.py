import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

st.set_page_config(
    page_title="FYP 2.0 - Intelligent Document Analysis System",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 FYP – Intelligent Document Analysis System")

st.markdown(
    """
Use the sidebar to:
- 📄 **Upload & ingest** resumes into the database  
- ❓ **Ask questions** over all ingested resumes or a specific one  

This is a thin Streamlit UI on top of the backend RAG system (PostgreSQL + pgvector, BGE embeddings, HF Router LLM).
"""
)
