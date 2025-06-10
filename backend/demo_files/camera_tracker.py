import cv2
import numpy as np
import os

def detect_objects_from_camera(ban_list, need_list, model_dir="../backend_support"):
    # Load YOLOv4 model
    config_path = os.path.join(model_dir, "yolov4.cfg")
    weights_path = os.path.join(model_dir, "yolov4.weights")
    names_path = os.path.join(model_dir, "coco.names")

    if not all(os.path.exists(p) for p in [config_path, weights_path, names_path]):
        raise FileNotFoundError("YOLO files not found in {}".format(model_dir))

    net = cv2.dnn.readNetFromDarknet(config_path, weights_path)
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    with open(names_path, 'r') as f:
        classes = [line.strip() for line in f.readlines()]

    cap = cv2.VideoCapture(0)
    user_missing_frames = 0
    user_threshold = 10

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
            net.setInput(blob)

            ln = net.getLayerNames()
            output_layers = [ln[i - 1] for i in net.getUnconnectedOutLayers()]
            detections = net.forward(output_layers)

            boxes = []
            class_ids = []
            confidences = []

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

            detected_labels = set()
            if len(indices) > 0:
                for i in indices.flatten():
                    label = classes[class_ids[i]]
                    detected_labels.add(label)
                    x, y, w, h = boxes[i]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0,255,0), 2)
                    cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)

            # Ban detection
            for banned in ban_list:
                if banned in detected_labels:
                    print(f"[!] Banned item detected: {banned}")

            # Need detection
            if any(item in detected_labels for item in need_list):
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

ban_list = ["cell phone", "tv"]
need_list = ["person"]
detect_objects_from_camera(ban_list, need_list)
