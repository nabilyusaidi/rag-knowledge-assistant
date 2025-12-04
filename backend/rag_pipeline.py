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
    return (
        f"Here are the retrieved resume sections from the database:\n\n"
        f"{context_text}\n\n"
        f"Question: {query}\n\n"
        f"Answer clearly and concisely based only on the context above."
    )

def get_system_prompt() -> str:
    return (
        "You are an assistant that answers questions about resumes.\n"
        "Use ONLY the provided context sections from the database.\n"
        "If the answer is not clearly contained in the context, say you don't know.\n"
        "Do NOT invent details that are not supported by the context."
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
        