import cv2
import numpy as np
import os
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# Global control variables
is_tracking_active = False
tracking_thread = None
stop_event = threading.Event()

class ObjectTracker:
    def __init__(self, model_dir="../backend_support"):
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
                banned_detected = False
                for banned in self.ban_list:
                    if banned in detected_labels:
                        print(f"[!] Banned item detected: {banned}")
                        banned_detected = True

                # Need detection
                user_present = any(item in detected_labels for item in self.need_list)
                if user_present:
                    user_missing_frames = 0
                else:
                    user_missing_frames += 1
                    if user_missing_frames >= user_threshold:
                        print("[!] User or essential item not detected for too long!")

                # Show frame
                cv2.imshow("Object Monitor", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()
            stop_event.clear()

# API Endpoints
@app.route('/start-tracking', methods=['POST'])
def start_tracking():
    global is_tracking_active, tracking_thread, stop_event
    
    if is_tracking_active:
        return jsonify({"status": "already running", "success": False})
    
    stop_event.clear()
    tracker = ObjectTracker()
    tracking_thread = threading.Thread(target=tracker.run_tracking, args=(stop_event,))
    tracking_thread.start()
    is_tracking_active = True
    
    return jsonify({"status": "tracking started", "success": True})

@app.route('/stop-tracking', methods=['POST'])
def stop_tracking():
    global is_tracking_active, tracking_thread, stop_event
    
    if not is_tracking_active:
        return jsonify({"status": "not running", "success": False})
    
    stop_event.set()
    tracking_thread.join()
    is_tracking_active = False
    
    return jsonify({"status": "tracking stopped", "success": True})

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"is_tracking_active": is_tracking_active})

if __name__ == '__main__':
    # Start the Flask server in a separate thread
    flask_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000})
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Control server running on http://localhost:5000")
    print("Endpoints:")
    print("POST /start-tracking - Start object tracking")
    print("POST /stop-tracking - Stop object tracking")
    print("GET /status - Check tracking status")
    
    # Keep the main thread alive
    try:
        while True:
            pass
    except KeyboardInterrupt:
        if is_tracking_active:
            stop_event.set()
            tracking_thread.join()
        print("Shutting down...")