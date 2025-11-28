from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

model_name = "HuggingFaceH4/zephyr-7b-beta"

_text_generation_pipeline = None #creating a global instance for this pipeline'

def get_generation_pipeline():
    global _text_generation_pipeline
    if _text_generation_pipeline is not None:
        return _text_generation_pipeline
    
    print(f"[llm] Loading Model: {model_name}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map = "auto",
        load_in_4bit = True,
        torch_dtype = "auto"
    )
    
    _text_generation_pipeline = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        return_full_text=False
    )
    
    print("[llm] Model loaded.")
    return _text_generation_pipeline

def build_prompt_structure(system_prompt: str, user_prompt: str) -> str:
    
    return(
        f"System: {system_prompt}\n\n"
        f"User: {user_prompt}\n\n"
        "Assistant:"
    )
    
def generate_answer(system_prompt: str, user_prompt: str, max_new_tokens: int = 512) -> str:
    
    pipe = get_generation_pipeline()
    prompt = build_prompt_structure(system_prompt, user_prompt)
    
    outputs = pipe(
        prompt,
        max_new_tokens = max_new_tokens,
        do_sample = True,
        temperature=0.3,
        top_p=0.9
    )
    
    generated_text = outputs[0]["generated_text"].strip()
    return generated_text

