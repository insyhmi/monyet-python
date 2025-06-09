from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import subprocess
from dotenv import load_dotenv
from demo_files import gemini_demo
from typing import List

import os

load_dotenv()

# CORS
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

class AppEntry(BaseModel):
    procrastinating: bool
    site: str

class AppData(BaseModel):
    data: List[AppEntry]
      

@app.post("/check")

async def check_focus(request: Request):
    data = await request.json()
    print("Received data at /check:", data)
    # Set data
    task = data['current_task']
    activity = data['current_window']

    isprocrastinating, score = gemini_demo.analyze_task_alignment(task, activity)
    isprocrastinating = bool (isprocrastinating)
    score = float(score)
    print(f"Gemini Procrastination Analysis -> isProcrastinating: {isprocrastinating}, score: {score}")
    return {
        "status": "ok",
        "current_task" : task,
        "current_window" : activity,
        "score" : score,
        "isProcrastinating" : isprocrastinating
        }


@app.post("/score")

async def calculate_score_data(app_data: AppData):
    """
    Calculates score and procrastination chain data

    SCORING SYSTEM:
    
    Single procrastination log = -0.2 PT
    Three-In-A-Row (30 s) procrastination log = -3.0PT
    Thirty-In-A-Row (5 mins) productivity log = +2.0PT

    """
    entries = app_data.data

    INTERVAL = 10  # Each entry is 10 seconds
    BLACKLIST_SCORE_PER_30S = -3
    PRODUCTIVE_SCORE_PER_5MINS = 2
    ISOLATED_PENALTY = -0.2

    total_blacklist_time = 0
    total_productive_time = 0
    isolated_penalty_count = 0
    procrastination_chains = []

    procrastination_chain = 0


    for i, entry in enumerate(entries):
        # Procrastination log found
        if entry.procrastinating:

            # Adds to current procrastination chain
            procrastination_chain += 1
            is_isolated = (
                (i == 0 or not entries[i - 1].procrastinating) and
                (i == len(entries) - 1 or not entries[i + 1].procrastinating)
            )
            if is_isolated:
                isolated_penalty_count += 1
            else:
                total_blacklist_time += INTERVAL

        # Productivity log found
        else:
            # Concludes current chain if exists and appends it
            if procrastination_chain > 0:
                procrastination_chains.append(procrastination_chain)
            procrastination_chain = 0
            total_productive_time += INTERVAL

    score = 0
    score += (total_blacklist_time // 30) * BLACKLIST_SCORE_PER_30S
    score += (total_productive_time // 300) * PRODUCTIVE_SCORE_PER_5MINS
    score += isolated_penalty_count * ISOLATED_PENALTY

    return {
        "score": round(score, 2),
        "details": {
            "blacklist_time_sec": total_blacklist_time,
            "productive_time_sec": total_productive_time,
            "isolated_blacklist_intervals": isolated_penalty_count,
            "procrastination_chain_list": procrastination_chain
        }
    }


print("FastAPI app is initialized:", app)