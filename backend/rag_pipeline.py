from typing import List, Tuple, Optional

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
    base = (
        "Here are the retrieved resume sections for a single candidate from the database:\n\n"
        f"{context_text}\n\n"
        "Task:\n"
        "Using ONLY the information in the resume sections above, rewrite the resume into a "
        "structured technical profile with the following exact section headings and numbering:\n\n"
        "1. Candidate Summary\n"
        "2. ML/AI Skills\n"
        "3. Software Engineering Skills\n"
        "4. Key Projects\n"
        "5. Experience Highlights\n"
        "Follow the rules given in the system prompt. Do not add any extra sections.\n"
    )
    
    query = query.strip()
    if query:
        base += f"\nAdditional user instruction: {query}\n"
        
    return base

def get_system_prompt() -> str:
    return (
        "You are an expert AI assistant that rewrites a candidate's resume into a "
        "concise, structured technical profile for recruiters and hiring managers.\n\n"
        "You must ALWAYS output using the exact sections below, in this order, "
        "with the exact headings and numbering:\n\n"
        
        "1. Candidate Summary\n"
        "2. ML/AI Skills\n"
        "3. Software Engineering Skills\n"
        "4. Key Projects\n"
        "5. Experience Highlights\n"
        "6. Suitable Roles\n\n"
        
        "RULES:\n"
        "- Use short paragraphs or bullet points under each section.\n"
        "- Do NOT narrate with phrases like 'This resume highlights...' or 'The candidate...'. "
        "Just write the profile directly.\n"
        "- Do NOT invent skills or experience that are not implied by the resume.\n"
        "- Be concise, technical, and recruiter-friendly.\n"
        "- Use ONLY the provided resume sections from the database.\n"
        "- If something is not clearly supported by the context, do not mention it.\n"
    )
    
def answer_query(query: str, top_k: int = 3, document_id: Optional[str] = None,) -> Tuple[str, List[RowType]]:
    

    rows = search_resume_sections(query_text=query, top_k=top_k, document_id=document_id)
    
    context_text = format_context(rows)
    
    system_prompt = get_system_prompt()
    user_prompt = build_user_prompt(query, context_text)
    
    answer = generate_answer(system_prompt, user_prompt)
    
    return answer, rows
        

if __name__ == "__main__":
    user_query = input("Ask a question about the resume: ")
    print("\nModel is thinking...\n")
    answer = answer_query(user_query, top_k=3)
    print("\n=== Answer ===\n")
    print(answer)
        