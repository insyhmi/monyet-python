from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import subprocess
from dotenv import load_dotenv
from demo_files import gemini_demo

import os

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with "http://localhost" or your app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Format for the current task
class TaskInput(BaseModel):
    current_task: str
    current_window: str


@app.post("/check")

async def check_focus(request: Request):
    data = await request.json()
    print("Received data at /check:", data)
    #print(type(data))
    task = data['current_task']
    activity = data['current_window']
    isprocrastinating, score = gemini_demo.analyze_task_alignment(task, activity)
    print(f"Gemini Procrastination Analysis -> isProcrastinating: {isprocrastinating}, score: {score}")
    return {"status": "ok", "received": data}


def check_focus(data: TaskInput):
    """
    Checks whether the current user task is related to the overall goal.

    """
    
    task = data.current_task.strip().lower()
    window = data.current_window.strip().lower()

    is_procrastinating = task not in window

    

print("FastAPI app is initialized:", app)