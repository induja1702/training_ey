"""
Used Deepface instead of HUME.AI
"""
import cv2
import json
import os
from deepface import DeepFace
import numpy as np


def analyze_video(video_path):
    """Sample frames from video and analyse emotions with DeepFace."""
    print(f"Analysing: {video_path}")

    cap     = cv2.VideoCapture(video_path)
    fps     = cap.get(cv2.CAP_PROP_FPS)
    results = []
    frame_n = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Analyse one frame per second
        if frame_n % int(fps) == 0:
            try:
                analysis = DeepFace.analyze(
                    frame,
                    actions=["emotion"],
                    enforce_detection=False
                )
                emotions  = analysis[0]["emotion"]
                dominant  = analysis[0]["dominant_emotion"]
                timestamp = frame_n / fps

                print(f"  [{timestamp:.1f}s]  dominant = {dominant}")
                results.append({
                    "timestamp_sec": round(timestamp, 2),
                    "dominant_emotion": dominant,
                    "emotions": emotions
                })
            except Exception as e:
                print(f"  [{frame_n}] skipped: {e}")

        frame_n += 1

    cap.release()
    print(f"\nAnalysed {len(results)} frames.")
    save_json(results)
    return results



def save_json(results):
    os.makedirs("results", exist_ok=True)
    with open("results/output.json", "w") as f:
        json.dump(results, f, indent=2, default=lambda o: float(o) if isinstance(o, np.floating) else str(o))
    print("Saved → results/output.json")