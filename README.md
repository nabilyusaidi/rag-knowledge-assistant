# FYP 2.0 — Intelligent Document Analysis System for Enterprise Knowledge Discovery
This project implements a production-oriented Retrieval-Augmented Generation (RAG) system
designed to support enterprise document understanding, semantic search, and ATS-style analysis
over unstructured documents such as resumes and job descriptions.

The system emphasizes clean backend architecture, cloud deployment readiness, and practical AI engineering trade-offs

## Project Overview
The system enables users (e.g. HR or internal teams) to:
   - Upload documents (resumes, PDFs)
   - Perform semantic search and question answering over documents
   - Analyze resume–job description alignment (ATS-style scoring)
   - Interact with an LLM-backed knowledge assistant through a web interface

The backend is implemented as a standalone Python package, while the frontend is delivered via Streamlit and deployed on Streamlit Cloud, backed by Supabase Postgres (pgvector).

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
- [] Evaluation and benchmarking (next phase)

## Tech Stack
- Programming Language: Python
- Backend: Custom Python package (RAG pipeline, retrieval, ATS logic)
- Frontend: Streamlit (multi-page)
- Database: Supabase PostgreSQL + pgvector
- LLM & Embeddings: HuggingFace models
- Deployment: Streamlit Cloud + Supabase
- Packaging: setuptools (pyproject.toml, setup.cfg)
