from openai import OpenAI
from typing import Tuple
import numpy as np

from dotenv import load_dotenv
import os

load_dotenv()

#############
"""
Demo with OpenAI API for checking the similarity of tasks

"""

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_contextual_embedding(text: str, context: str = "") -> np.ndarray:
    """Enhanced embedding format with task context"""

    enriched_text = f"Task context: {context}\nCurrent activity: {text}" if context else text
    response = client.embeddings.create(
        input=[enriched_text],
        model="text-embedding-3-large"  # More accurate than 'small'
    )
    return np.array(response.data[0].embedding)


def is_procrastinating(main_task: str, current_activity: str, threshold: float = 0.65) -> Tuple[bool, float, str]:
    """
    Determines if user is procrastinating with improved logic
    Returns: (is_procrastinating, similarity_score)
    """

    # Heuristic task categories - CAN BE CHANGED
    productive_keywords = ["work", "study", "research"]
    distracting_keywords = ["social media", "game", "movie", "shopping"]
    
    # Get enhanced embeddings
    task_embedding = get_contextual_embedding(main_task, "productive work")
    activity_embedding = get_contextual_embedding(current_activity, "current focus")
    
    # Calculate similarity
    similarity = np.dot(task_embedding, activity_embedding) / (
        np.linalg.norm(task_embedding) * np.linalg.norm(activity_embedding)
    )
    
    # Enhanced decision logic
    is_distraction = (
        similarity < threshold or
        any(word in current_activity.lower() for word in distracting_keywords)
    )

    if is_distraction:
        if similarity < threshold:
            reason = "Different tokenization"
        elif any(word in current_activity.lower() for word in distracting_keywords):
            reason = "Heuristics"
    else:
        if similarity >= threshold:
            reason = "Similar tokenization"
        else:
            reason = None
    
    return (is_distraction, similarity, reason)


#################
# EXAMPLE USAGE #
#################

# Task at hand
task = "League of Legends team practice"

# List of activities to compare to
activities = [
    "MOBA Tier List 2025",  
    "Watching YouTube tutorials on push-ups",  
    "Sleep schedules",
    "How to bake - YouTube"  
]

for activity in activities:
    result, score, reason = is_procrastinating(task, activity)
    print(f"Task: '{task}' vs Activity: '{activity}'")
    print(f"Similarity: {score:.2f} -> {'DISTRACTION' if result else 'ON TASK'} because {reason}\n")
