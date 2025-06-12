from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import subprocess
from dotenv import load_dotenv
from demo_files import gemini_demo
import numpy as np
import threading
import cv2

from typing import List, Tuple, Optional
from contextlib import asynccontextmanager

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
    geminiScore: float

class AppData(BaseModel):
    data: List[AppEntry]


class AdaptRequest(BaseModel):
    focus_length: int
    blacklist_time_sec: int
    productive_time_sec: int
    isolated_blacklist_intervals: int
    procrastination_chain_list: List[Tuple[int, int, int]]  # (length, start_index, end_index)
    
stop_event = threading.Event()
is_tracking_active = False
tracking_thread = None
latest_detection = dict()
class TrackingStatus(BaseModel):
    is_active: bool
    last_detection: Optional[dict]

class ObjectTracker:
    def __init__(self, model_dir="backend_support"):
        self.PATH = os.path.dirname(__file__)
        self.ban_list = ["cell phone", "tv"]
        self.need_list = ["person"]
        
        # Load YOLOv4 model
        config_path = os.path.join(self.PATH, model_dir, "yolov4.cfg")
        weights_path = os.path.join(self.PATH, model_dir, "yolov4.weights")
        names_path = os.path.join(self.PATH, model_dir, "coco.names")

        if not all(os.path.exists(p) for p in [config_path, weights_path, names_path]):
            raise FileNotFoundError("YOLO files not found in {}".format(model_dir))

        self.net = cv2.dnn.readNetFromDarknet(config_path, weights_path)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        with open(names_path, 'r') as f:
            self.classes = [line.strip() for line in f.readlines()]

    def run_tracking(self, stop_event):
        global latest_detection
        
        cap = cv2.VideoCapture(0)
        user_missing_frames = 0
        user_threshold = 10

        try:
            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    break

                blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
                self.net.setInput(blob)

                ln = self.net.getLayerNames()
                output_layers = [ln[i - 1] for i in self.net.getUnconnectedOutLayers()]
                detections = self.net.forward(output_layers)

                boxes = []
                class_ids = []
                confidences = []
                detected_labels = set()

                for output in detections:
                    for det in output:
                        scores = det[5:]
                        class_id = np.argmax(scores)
                        confidence = scores[class_id]

                        if confidence > 0.5:
                            w, h = int(det[2]*frame.shape[1]), int(det[3]*frame.shape[0])
                            x = int(det[0]*frame.shape[1] - w/2)
                            y = int(det[1]*frame.shape[0] - h/2)
                            boxes.append([x, y, w, h])
                            class_ids.append(class_id)
                            confidences.append(float(confidence))

                indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

                if len(indices) > 0:
                    for i in indices.flatten():
                        label = self.classes[class_ids[i]]
                        detected_labels.add(label)
                        x, y, w, h = boxes[i]
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0,255,0), 2)
                        cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)

                # Ban detection
                banned_detected = any(banned in detected_labels for banned in self.ban_list)

                # Need detection
                user_present = any(item in detected_labels for item in self.need_list)
                if user_present:
                    user_missing_frames = 0
                else:
                    user_missing_frames += 1
                    if user_missing_frames >= user_threshold:
                        print("[!] User or essential item not detected for too long!")

                # Update latest detection
                latest_detection = {
                    "detected_objects": list(detected_labels),
                    "banned_items_detected": banned_detected,
                    "user_present": user_present,
                    "frame_size": frame.shape[:2] if ret else None
                }

                # Show frame
                cv2.imshow("Object Monitor", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()
            stop_event.clear()

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
    if activity == 'Procrastination Detector':
        isprocrastinating = False
        score = 0.65
    print(f"Gemini Procrastination Analysis -> isProcrastinating: {isprocrastinating}, score: {score}")
    return {
        "status": "ok",
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
    chain_start = None
    chain_end = None

    print("Received data at /score:", app_data)

    """for i, entry in enumerate(entries):
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

    print(round(score, 2))
    print(total_productive_time)
    

    return {
        "score": round(score, 2),
        "details": {
            "blacklist_time_sec": total_blacklist_time,
            "productive_time_sec": total_productive_time,
            "isolated_blacklist_intervals": isolated_penalty_count,
            "procrastination_chain_list": procrastination_chains # chains, start and end (not based on timestamp yet)

        }
    }"""
    score =0
    ai_score = 0
    length =0
    for i, e in enumerate(app_data.data):
        length += 1
        ai_score += e.geminiScore
        if e.procrastinating:
            score -= 1
        else:
            score += 1

    return {
        "score" : round(((score / length) * 100 + (ai_score *100/ length)) /2, 2)
    }

@app.post("/camera-scan")

def scan():
    ban_list = ["cell phone", "tv"]
    need_list = ["person"]
    result = scan_camera_frame(ban_list, need_list)
    return result

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



@app.post("/start-tracking")
def start_tracking():
    global is_tracking_active, tracking_thread, stop_event
    
    if is_tracking_active:
        raise HTTPException(status_code=400, detail="Tracking is already active")
    
    stop_event.clear()
    tracker = ObjectTracker()
    tracking_thread = threading.Thread(target=tracker.run_tracking, args=(stop_event,))
    tracking_thread.daemon = True
    tracking_thread.start()
    is_tracking_active = True
    
    return {"status": "tracking started", "success": True}

@app.post("/stop-tracking")
def stop_tracking():
    global is_tracking_active, tracking_thread, stop_event
    
    if not is_tracking_active:
        raise HTTPException(status_code=400, detail="Tracking is not active")
    
    stop_event.set()
    tracking_thread.join(timeout=2)
    is_tracking_active = False
    
    return {"status": "tracking stopped", "success": True}

@app.get("/status", response_model=TrackingStatus)
def get_status():
    return {
        "is_active": is_tracking_active,
        "last_detection": latest_detection
    }

@app.on_event("shutdown")
def shutdown_event():
    global is_tracking_active, stop_event
    if is_tracking_active:
        stop_event.set()


print("FastAPI app is initialized:", app)
