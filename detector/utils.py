from ultralytics import YOLO
import cv2
import numpy as np

model = YOLO("detector/yolo/best.pt")

def predict_image(img):
    results = model(img)[0]
    return results.plot()

def predict_video(path):
    cap = cv2.VideoCapture(path)
    out_frames = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        result = model(frame)[0]
        out_frames.append(result.plot())

    cap.release()
    return out_frames
