import psycopg2
from pypdf import PdfReader

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "rag-knowledge-assistant"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

def get_connection():
    conn = psycopg2.connect(
        host = DB_HOST,
        port = DB_PORT,
        dbname = DB_NAME,
        user = DB_USER,
        password = DB_PASSWORD,
    )
    
    return conn

def insert_document(cursor, title, source_path):
    cursor.execute(
        """
        INSERT INTO documents (title, source_path)
        VALUES (%s, %s)
        RETURNING id
        """,
        (title, source_path),
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

def insert_sections(cursor, document_id, sections):
    for section in sections:
        cursor.execute(
            """
            INSERT INTO resume_sections
            (document_id, section_label, section_index, content)
            VALUES (%s,%s,%s,%s)
            """,
            (document_id, section["label"], section["index"], section["content"])
        )
    
def main(pdf_path):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Insert Document Row
        title = pdf_path.split("/")[-1]
        document_id = insert_document(cursor, title, pdf_path)
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
        insert_sections(cursor, document_id, sections)

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
    
    PDF_PATH = "C:/Users/A/OneDrive/Projects/rag-knowledge-assistant/data/Nabil Yusaidi Resume.pdf"
    main(PDF_PATH)
