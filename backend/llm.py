from openai import OpenAI
from google import genai
from typing import Any, List, Dict

import os
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "gemini-3-flash-preview"
FALLBACK_MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct:featherless-ai"

_client = None
_fallback_client = None

def get_llm() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=os.getenv("GEMINI_API_KEY"),
        )
    return _client

def _get_fallback_llm() -> OpenAI:
    global _fallback_client
    if _fallback_client is None:
        _fallback_client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_TOKEN"),
        )
    return _fallback_client

def build_prompt_structure(system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
    
    return[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
def generate_answer(system_prompt: str, user_prompt: str, max_new_tokens: int = 2048) -> str:
    messages = build_prompt_structure(system_prompt, user_prompt)

    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=max_new_tokens,
            top_p=0.9,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Primary model failed ({e}), switching to fallback...")
        client = _get_fallback_llm()
        response = client.chat.completions.create(
            model=FALLBACK_MODEL_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=max_new_tokens,
            top_p=0.9,
        )
        return response.choices[0].message.content.strip()

