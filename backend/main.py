from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import subprocess
from dotenv import load_dotenv
from demo_files import gemini_demo

from typing import List, Tuple
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


class AdaptRequest(BaseModel):
    focus_length: int
    blacklist_time_sec: int
    productive_time_sec: int
    isolated_blacklist_intervals: int
    procrastination_chain_list: List[Tuple[int, int, int]]  # (length, start_index, end_index)


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
        "current_window" : activity,
        "score" : score,
        "isProcrastinating" : isprocrastinating


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
    chain_start = None
    chain_end = None


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
            
            if procrastination_chain == 1:
                chain_start = i
                chain_end = None

        # Productivity log found
        else:
            # Concludes current chain if exists and appends it
            if procrastination_chain > 0:
                chain_end = i
                procrastination_chains.append((procrastination_chain, chain_start, chain_end))
                procrastination_chain = 0

            total_productive_time += INTERVAL
    
    # Edge case
    if procrastination_chain > 0:
        chain_end = len(entries)
        procrastination_chains.append((procrastination_chain, chain_start, chain_end))

    score = 0
    score += (total_blacklist_time // 30) * BLACKLIST_SCORE_PER_30S
    score += (total_productive_time // 300) * PRODUCTIVE_SCORE_PER_5MINS
    score += isolated_penalty_count * ISOLATED_PENALTY

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
            "procrastination_chain_list": procrastination_chains # chains, start and end (not based on timestamp yet)

        }
    }


@app.post("/adapt")

async def procrastination_analysis(data: AdaptRequest):
    """Gives comments based on procrastination"""
    if data.focus_length <= 0:
        return {"recommendations": ["Focus session length not detected."]}

    if not data.procrastination_chain_list:
        return {"recommendations": ["No procrastination logs recorded. Well done!"]}
    
    recommendations = []

    focus_chain_count = -(-data.focus_length // 10)

    total_chains = len(data.procrastination_chain_list)
    long_chains = [c for c in data.procrastination_chain_list if c[0] >= 20]  # ≥10 min
    average_chains = [c for c in data.procrastination_chain_list if (c[0] >= 3 and c[0] <= 20)]
    short_chains = [c for c in data.procrastination_chain_list if c[0] < 3]
    early_chains = [c for c in data.procrastination_chain_list if c[1] < 5]
    late_chains = [c for c in data.procrastination_chain_list if c[2] > (len(data.procrastination_chain_list) - 5)]

    # Long procrastination chain detected
    if len(long_chains) >= 0.3 * (focus_chain_count / 20):
        recommendations.append(
            "Too much procrastination! Perhaps choose a better time and place to do your work?"
        )
    elif long_chains:
        recommendations.append(
            "Detected long procrastination chains (>15 min). Consider splitting your focus blocks into shorter chunks (e.g. 15-minute sprints)."
        )

    # Procrastination chains bunched up at the beginning
    if early_chains and not late_chains:
        recommendations.append(
            "Most procrastination occurred early in the session. Warming up is fine - but perhaps do it BEFORE the session."
        )
    # Procrastination chains bunched up at the end
    elif late_chains and not early_chains:
        recommendations.append(
            "Procrastination increased toward the end. You might be fatigued—try shortening your focus duration by a few minutes or take more frequent breaks."
        )
    # Procrastination chains at the beginning and end:
    elif late_chains and early_chains:
        recommendations.append(
            "Procrastination present at the beginning and end. Shorten your focus timer, or mentally prepare beforehand!"
        )
    
    # Procrastination chains spread out, no long chains
    if len(short_chains) >= 5 and not long_chains:
        recommendations.append(
            "Procrastination is spread out in small chunks. You're close to staying on track—work on minimizing distractions to improve further."
        )
    
    if len(average_chains) >= 0.3 * (focus_chain_count / 10):
        recommendations.append(
            "Consistent procrastination throughout the session. Try harder next time!"
        )

    # Good job
    if not recommendations:
        recommendations.append("No major procrastination trends detected. Good job! Keep it up!")

    return {"recommendations": recommendations}

print("FastAPI app is initialized:", app)