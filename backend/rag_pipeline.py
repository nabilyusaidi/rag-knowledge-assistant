from typing import List, Tuple

from backend.ingestion import get_connection
from backend.retrieval import search_resume_sections
from backend.llm import generate_answer

RowType = Tuple[int, str, str, float, float] # this is for resume_section returns where it gives id, section_label, content, cosine_distance, cosine_similarity

def format_context(rows: List[RowType]) -> str:
    
    lines = []
    
    for rank, row in enumerate(rows, start=1):
        section_id = row[0]
        section_label = row[1]
        content = row[2]
        cosine_dist = float(row[3])
        cosine_sim = float(row[4])

        header = (
            f"[Rank {rank} | ID {section_id} | {section_label} | "
            f"cos_sim={cosine_sim:.4f}]"
        )
        lines.append(header)
        lines.append(content)
        lines.append("") 

    return "\n".join(lines)

def build_user_prompt(query: str, context_text: str) -> str:
    return f""" You are given several resume sections retrieved from a vector database.
Use ONLY this information to answer  the question.

Question: {query}
Relevant Resume Sections: {context_text}

If the context does not contain the answer, say you don't know based on the available information.
"""

def get_system_prompt()-> str:
    return(
        "You are an intelligent document analysis assistant for resumes. "
        "You answer questions based strictly on the provided resume sections. "
        "Be concise, factual, and avoid making up information not supported "
        "by the context. If you are unsure or the context is insufficient, "
        "explicitly say so."
    )
    
def answer_query(query: str, top_k: int = 3)-> str:
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        rows = search_resume_sections(cursor, query_text = query, top_k=top_k)
        
        context_text = format_context(rows)
        
        system_prompt = get_system_prompt()
        user_prompt = build_user_prompt(query, context_text)
        
        final_answer = generate_answer(system_prompt, user_prompt)
        
        return final_answer
    
    finally:
        cursor.close()
        conn.close()
        

if __name__ == "__main__":
    user_query = input("Ask a question about the resume: ")
    print("\nModel is thinking...\n")
    answer = answer_query(user_query, top_k=3)
    print("\n=== Answer ===\n")
    print(answer)
        