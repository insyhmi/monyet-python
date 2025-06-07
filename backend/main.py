from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()

OpenAI.api_key = "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"

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