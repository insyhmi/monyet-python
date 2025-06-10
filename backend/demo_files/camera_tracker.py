import cv2
import cvlib as cv
from cvlib.object_detection import draw_bbox
import numpy as np
import os

# Define paths (go back one folder to access backend_support)
def track_procrastination(ban_list, need_list):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Goes up one level
    model_config = os.path.join(base_dir, "backend_support", "yolov4.cfg")
    model_weights = os.path.join(base_dir, "backend_support", "yolov4.weights")
    classes_file = os.path.join(base_dir, "backend_support", "coco.names")

    # Check if files exist
    if not all(os.path.exists(f) for f in [model_config, model_weights, classes_file]):
        raise FileNotFoundError("YOLO model files not found in ../backend_support/")

    # Load YOLO model
    net = cv2.dnn.readNetFromDarknet(model_config, model_weights)
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)  # Use DNN_TARGET_CUDA for GPU

    # Load class names
    with open(classes_file, 'r') as f:
        classes = [line.strip() for line in f.readlines()]

    # Open webcam
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 1) Face detection (using cvlib)
        faces, face_confidences = cv.detect_face(frame)
        face_detected = len(faces) > 0

        # 2) Object detection (custom YOLOv4 via OpenCV DNN)
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
        net.setInput(blob)
        layer_names = net.getLayerNames()
        output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
        layer_outputs = net.forward(output_layers)

        boxes, confidences, class_ids = [], [], []

        for output in layer_outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > 0.5:  # Confidence threshold
                    center_x = int(detection[0] * frame.shape[1])
                    center_y = int(detection[1] * frame.shape[0])
                    w = int(detection[2] * frame.shape[1])
                    h = int(detection[3] * frame.shape[0])
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        # Apply Non-Max Suppression (NMS)
        indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        
        # Prepare final detections
        final_boxes = []
        final_labels = []
        final_confidences = []

        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = boxes[i]
                final_boxes.append([x, y, x + w, y + h])
                final_labels.append(classes[class_ids[i]])
                final_confidences.append(confidences[i])

        # Draw results (using cvlib's draw_bbox for consistency)
        try:
            out = draw_bbox(frame, final_boxes, final_labels, final_confidences)
        except TypeError:
            print(f"{final_labels} not in list")
        
        # Display
        cv2.imshow("Tracking", out)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Checking for procrastination

        user_threshold = 10
        user_missing = 0

        if len(final_boxes) > 0:
            for i in range(len(final_boxes)):
                label = final_labels[i]
                confidence = final_confidences[i]
                
                print(f"Detected: {label} (Confidence: {confidence:.2f})")
                
                # Banned item found
                if label in ban_list:
                    yield label, True # Presence of item

                # User not found for more than 10 seconds
                if label not in need_list:
                    user_missing += 1

                if label in need_list:
                    user_missing = 0

                if user_missing == user_threshold:
                    yield label, False # Lack of item
                
    cap.release()
    cv2.destroyAllWindows()

    return

def main():
    ban_list = ["cell phone"]
    need_list = ["person"]
    for output in track_procrastination(ban_list, need_list):
        val = -1

        if len(output) == 2:
            item = output[0]
            val = output[1]

            if val == True:
                print("Procrastination item detected. Cease usage immediately.")
            elif val == False:
                print("User not found. Return immediately.")
                
        elif output == -1:
            break
        

main()
