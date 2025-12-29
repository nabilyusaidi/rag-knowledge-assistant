from openai import OpenAI
from typing import Any, List, Dict

import os

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct:featherless-ai"

_client = None

def get_llm()-> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN"),
        )
        
    return _client

def build_prompt_structure(system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
    
    return[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
def generate_answer(system_prompt: str, user_prompt: str, max_new_tokens: int = 512) -> str:
    client = get_llm()

    messages = build_prompt_structure(system_prompt, user_prompt)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.3,
        max_tokens=max_new_tokens,
        top_p=0.9,
    )

    return response.choices[0].message.content.strip()

