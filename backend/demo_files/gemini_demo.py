import google.generativeai as genai  # Correct import
import numpy as np
from dotenv import load_dotenv
import os

load_dotenv()

print(f"Gemini key loaded? {os.getenv('GEMINI_API_KEY') is not None}")


# Configuration
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise EnvironmentError("GEMINI_API_KEY not found in environment. Check your .env file.")

genai.configure(api_key=api_key, transport="rest")  # Get from https://aistudio.google.com/app/apikey

for model in genai.list_models(): 
    print(model.name, model.supported_generation_methods)


def get_embedding(text: str, model: str = "models/embedding-001") -> list[float]:
    """Get embeddings using Gemini's API"""
    result = genai.embed_content(
        model=model,
        content=text,
        task_type="retrieval_query" if "?" in text else "retrieval_document"
    )
    return result['embedding']


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between vectors"""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    return np.dot(a, b) / (a_norm * b_norm)


def analyze_task_alignment(main_task: str, current_activity: str) -> tuple[bool, float]:
    """
    Determine if user is procrastinating using Gemini
    Returns: (is_procrastinating, similarity_score)
    """
    # Get embeddings
    task_embed = get_embedding(main_task)
    activity_embed = get_embedding(current_activity)
    
    # Calculate base similarity
    embedding_similarity = cosine_similarity(task_embed, activity_embed)
    
    # Get contextual analysis from Gemini
    prompt = f"""Rate task alignment between:
    Main Task: '{main_task}'
    Current Activity: '{current_activity}'
    
    Consider:
    - Direct relevance (e.g. 'coding' vs 'IDE')
    - Indirect benefits (e.g. 'research' vs 'reading papers')
    - Common distractions
    - The features of the website or application involved
    
    Provide ONLY a float (0-1) where 1=perfect alignment:"""
    
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    response = model.generate_content(prompt)
    try:
        llm_score = min(max(float(response.text.strip()), 0.0), 1.0)  # Clamp to 0-1
    except (ValueError, AttributeError):
        llm_score = 0.5  # Fallback value
    
    # Combined score (weighted average)
    combined_score = (embedding_similarity * 0.6) + (llm_score * 0.4)
    return combined_score < 0.65, combined_score  # Threshold adjustable


# Task at hand
task = "Doing maths"

# List of activities to compare to
activities = [
    "Desmos",
    "YouTube - Studying John Rawls until I fucking faint"
]

"""for activity in activities:
     isprocrastinating, score = analyze_task_alignment(task, activity)
     print(f"Task: '{task}' vs Activity: '{activity}'")
     print(f"Similarity: {score:.2f} -> {'DISTRACTION' if isprocrastinating else 'ON TASK'}\n")"""