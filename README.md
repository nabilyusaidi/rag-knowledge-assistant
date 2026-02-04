# FYP 2.0 — Intelligent Document Analysis System for Enterprise Knowledge Discovery
This project implements a production-oriented Retrieval-Augmented Generation (RAG) system
designed to support enterprise document understanding, semantic search, and ATS-style analysis
over unstructured documents such as resumes and job descriptions.

The system emphasizes clean backend architecture, cloud deployment readiness, and practical AI engineering trade-offs

## System Architecture & Flow

### 1. Ingestion Layer (`backend/ingestion.py`, `backend/create_job_post.py`)
- **PDF Processing**: Resumes are ingested via `pypdf`, cleaned, and parsed into raw text.
- **Job Posts**: Job Descriptions (JDs) are created and stored as documents, served as the ground truth for ATS scoring.
- **Chunking & Embedding**: Text is chunked and embedded using HuggingFace models (e.g., BGE) before storage.

### 2. Storage Layer (`Supabase PostgreSQL + pgvector`)
- **Documents Table**: Stores metadata and file paths.
- **Document Sections**: Stores chunked text with vector embeddings for semantic search.
- **Applications Link**: Connects Candidates (Resumes) to Job Posts for many-to-many relationship management.

### 3. Analysis Layer (`backend/ats.py`, `backend/analytics.py`)
- **Deterministic ATS Scoring**:
  - Extracts skills from JDs and Resumes using regex and set operations.
  - Calculates a weighted score (70% Must-Have, 30% Nice-To-Have).
  - Identifies missing skills and gaps.
- **Analytics**: Aggregates data on department performance, role popularity, and application funnel stats.

### 4. RAG & Interaction Layer (`backend/rag_pipeline.py`, `backend/llm.py`)
- **Semantic Search**: helper functions in `backend/retrieval.py` fetch relevant resume sections based on user query.
- **LLM Generation**: Uses Gemini (via `backend/llm.py`) to synthesize answers or rewrite resumes into structured profiles.
- **Streamlit Frontend**: A multi-page UI (`frontend/app.py`, `frontend/pages/`) for:
  - Uploading docs
  - Viewing analytics dashboards
  - Chatting with the knowledge base
  - Managing job posts

## Current Status
- [x] Project initialized
- [x] Backend package structure finalized
- [x] PDF ingestion pipeline implemented (PyPDF-based)
- [x] Text chunking and embedding generation
- [x] pgvector-based semantic retrieval
- [x] Resume section parsing and structured storage
- [x] RAG pipeline (retrieval + LLM orchestration)
- [x] ATS-style resume–JD matching logic
- [x] Streamlit multi-page frontend
- [x] Supabase Postgres integration (cloud deployment)
- [x] Streamlit Cloud deployment
- [ ] Evaluation and benchmarking (next phase)

## Future Roadmap & Recommendations

### Future Improvements
- **Asynchronous Processing**: Move PDF ingestion and embedding generation to a background worker (e.g., Celery or RQ) to prevent UI blocking during large uploads.
- **Advanced Semantic Matching**: Replace exact keyword matching in ATS logic with embedding-based similarity to capture synonyms (e.g., "ML" vs. "Machine Learning").
- **Hybrid Search**: Combine keyword search (BM25) with vector search (Reciprocal Rank Fusion) for better retrieval accuracy.

## Tech Stack
- Programming Language: Python
- Backend: Custom Python package (RAG pipeline, retrieval, ATS logic)
- Frontend: Streamlit (multi-page)
- Database: Supabase PostgreSQL + pgvector
- LLM & Embeddings: HuggingFace models, Gemini
- Deployment: Streamlit Cloud + Supabase
- Packaging: setuptools (pyproject.toml, setup.cfg)
