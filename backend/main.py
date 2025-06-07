from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI

from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Format for the current task
class TaskInput(BaseModel):
    current_task: str
    current_window: str


@app.post("/check")
def check_focus(data: TaskInput):
    """
    Checks whether the current user task is related to the overall goal.

    """
    
    task = data.current_task.lower()
    window = data.current_window.lower()

    is_procrastinating = task not in window

    return {
        "procrastinating": is_procrastinating,
        "reason": "Window does not match task" if is_procrastinating else "On task"
    }

print("FastAPI app is initialized:", app)