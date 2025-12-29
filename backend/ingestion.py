import psycopg2, os
from psycopg2.extras import Json
from pypdf import PdfReader
from pathlib import Path
import streamlit as st

def get_connection():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        port=int(st.secrets["DB_PORT"]),
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        sslmode="require",
    )
def insert_document(cursor, title, source_path, doc_type="resume"):
    doc_metadata={
        "doc_type": doc_type,
        "title": title,
        "source_path": source_path
    }
    cursor.execute(
        """
        INSERT INTO documents (title, doc_type, source_path, metadata)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (title, doc_type, source_path, Json(doc_metadata)),
    )
    
    document_id = cursor.fetchone()[0]
    return document_id

def read_pdf_text(pdf_path):
    reader = PdfReader(pdf_path)
    all_text = ""
    
    for page in reader.pages:
        text = page.extract_text() or "" # if the text is None, it will fall back to an empty string so that text is always a string
        all_text += text + "\n" # append pages text into all_text and add newline(\n) between pages to avoid merge into one long line
    
    return all_text
    
def clean_text(text):
    text = text.replace("\r", "\n") #sometimes pdf has the windows line endings eg: Experience\r\n
    
    lines = text.split("\n") #split whenever the iteration sees \n in each line
    
    lines = [line.strip() for line in lines] #line.strip removes whitespaces
    
    lines = [line for line in lines if line] #removes empty lines
    
    return "\n".join(lines) #once done the cleaning it will rejoin the lines back into one string

def extract_sections(cleaned_text):
    summary_keywords = ["summary", "profile", "objective"]
    experience_keywords = ["experience", "employment", "work history"]
    education_keywords = ["education", "academic"]
    project_keywords = ["relevant projects", "projects"]
    
    sections= { #create lists for each section
        "summary": [],
        "experience": [],
        "education": [],
        "projects": []
    }
    
    current_label = None
    
    for line in cleaned_text.split("\n"):
        lower = line.lower() #converts each line into lowercase
        
        if any(keyword in lower for keyword in summary_keywords):
            current_label = "summary"
            continue
        
        if any(keyword in lower for keyword in experience_keywords):
            current_label = "experience"
            continue
        
        if any(keyword in lower for keyword in education_keywords):
            current_label = "education"
            continue
        
        if any(keyword in lower for keyword in project_keywords):
            current_label = "projects"
            continue
        
        if current_label is not None:
            sections[current_label].append(line)
    
    result = []
    index = 0

    for label in ["summary", "experience", "education", "projects"]:
        content_lines = sections[label]
        content = "\n".join(content_lines).strip()
        
        if content:
            result.append(
                {
                    "label": label,
                    "index": index,
                    "content": content
                }
            )
            index += 1
            
    return result

def insert_sections(cursor, document_id, sections, doc_type="resume"):
    for section in sections:
        section_metadata={
            "doc_type": doc_type,
            "section_label": section["label"],
            "section_index": section["index"]
        }
        cursor.execute(
            """
            INSERT INTO document_sections
            (document_id, section_label, section_index, content, metadata)
            VALUES (%s,%s,%s,%s, %s)
            """,
            (document_id, section["label"], section["index"], section["content"], Json(section_metadata))
        )
    
def batch_ingestion(folder_path):
    folder_path = os.path.abspath(folder_path)
    
    if not os.path.isdir(folder_path):
        print("Folder does not exist:", folder_path)
        return
    
    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(".pdf"):
            continue
        
        pdf_path = os.path.join(folder_path, filename)
        
        try:
            main(pdf_path)
        except Exception as e:
            print("Error ingesting", pdf_path, ":", e)


def main(pdf_path):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Insert Document Row
        title = Path(pdf_path).name
        document_id = insert_document(cursor, title, pdf_path, doc_type="resume")
        print ("Inserted document ID:", document_id)
        
        # Read PDF
        raw_text = read_pdf_text(pdf_path)
        print("Raw text length:", len(raw_text))

        # Clean text
        cleaned = clean_text(raw_text)
        print("Cleaned text length:", len(cleaned))

        # Extract sections (summary, experience, education)
        sections = extract_sections(cleaned)
        print("Extracted section labels:", [s["label"] for s in sections])

        # Insert sections
        insert_sections(cursor, document_id, sections, doc_type="resume")

        # Commit changes to DB
        conn.commit()
        print("Ingestion completed.")
        
    except Exception as e:
        conn.rollback()
        print("Error during Ingestion:", e)
        
    finally:
        cursor.close()
        conn.close()
  
if __name__ == "__main__":
    
    # PDF_PATH = "C:/Users/A/OneDrive/Projects/rag-knowledge-assistant/data/Nabil Yusaidi Resume.pdf"
    # main(PDF_PATH)
    
    FOLDER_PATH = "C:/Users/A/OneDrive/Projects/rag-knowledge-assistant/data/Data Science"
    batch_ingestion(FOLDER_PATH)
