# import asyncio, json
# from hume import AsyncHumeClient
# from hume.expression_measurement.batch import Face, Prosody
# from hume import HumeBatchClient
#
# from config import HUME_API_KEY
#
# client = AsyncHumeClient(api_key=HUME_API_KEY)
#
# async def analyze_video(video_path):
#
#     config = {
#         "face": Face(),
#         "prosody": Prosody()
#     }
#
#     job = await client.expression_measurement.batch.start_inference_job(
#         urls=[],
#         files=[video_path],
#         models=config
#     )
#
#     job_id = job.job_id
#     print("Job ID:", job_id)
#
#     predictions = await client.expression_measurement.batch.get_job_predictions(
#         job_id
#     )
#
#     return predictions
#
#
# def save_json(results):
#
#     with open("results/output.json", "w") as f:
#         json.dump(results, f, indent=2)
#
#     print("Saved")

# hume_client.py
# import json
# import time
# import requests
#
# from config import HUME_API_KEY
#
# BATCH_URL = "https://api.hume.ai/v0/batch/jobs"
# HEADERS   = {"X-Hume-Api-Key": HUME_API_KEY}
#
#
# def analyze_video(video_path):
#     """Upload video, wait for job, return predictions."""
#
#     # 1. Submit job
#     print("Submitting job to Hume.ai...")
#     with open(video_path, "rb") as f:
#         resp = requests.post(
#             BATCH_URL,
#             headers=HEADERS,
#             files={"file": (video_path, f, "video/mp4")},
#             data={"json": json.dumps({"models": {"face": {}, "prosody": {}}})}
#         )
#
#     if resp.status_code not in (200, 201):
#         raise RuntimeError(f"Submit failed {resp.status_code}: {resp.text}")
#
#     job_id = resp.json()["job_id"]
#     print(f"Job ID: {job_id}")
#
#     # 2. Poll until complete
#     print("Waiting for results", end="", flush=True)
#     while True:
#         status_resp = requests.get(f"{BATCH_URL}/{job_id}", headers=HEADERS)
#         status = status_resp.json().get("state", {}).get("status", "")
#         print(".", end="", flush=True)
#
#         if status == "COMPLETED":
#             print(" done!")
#             break
#         if status in ("FAILED", "ERROR"):
#             raise RuntimeError(f"Job failed: {status_resp.json()}")
#
#         time.sleep(5)
#
#     # 3. Fetch predictions
#     pred_resp = requests.get(f"{BATCH_URL}/{job_id}/predictions", headers=HEADERS)
#     return pred_resp.json()
#
#
# def save_json(results):
#     import os
#     os.makedirs("results", exist_ok=True)
#     with open("results/output.json", "w") as f:
#         json.dump(results, f, indent=2)
#     print("Saved → results/output.json")

"""

Used Deepface instead of HUME.AI
"""
# hume_client.py  — uses DeepFace instead of Hume.ai
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