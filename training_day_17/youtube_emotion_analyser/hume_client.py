import json
import time
import requests

from config import HUME_API_KEY

BATCH_URL = "https://api.hume.ai/v0/batch/jobs"
HEADERS   = {"X-Hume-Api-Key": HUME_API_KEY}


def analyze_video(video_path):
    """Upload video, wait for job, return predictions."""

    # 1. Submit job
    print("Submitting job to Hume.ai...")
    with open(video_path, "rb") as f:
        resp = requests.post(
            BATCH_URL,
            headers=HEADERS,
            files={"file": (video_path, f, "video/mp4")},
            data={"json": json.dumps({"models": {"face": {}, "prosody": {}}})}
        )

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Submit failed {resp.status_code}: {resp.text}")

    job_id = resp.json()["job_id"]
    print(f"Job ID: {job_id}")

    # 2. Poll until complete
    print("Waiting for results", end="", flush=True)
    while True:
        status_resp = requests.get(f"{BATCH_URL}/{job_id}", headers=HEADERS)
        status = status_resp.json().get("state", {}).get("status", "")
        print(".", end="", flush=True)

        if status == "COMPLETED":
            print(" done!")
            break
        if status in ("FAILED", "ERROR"):
            raise RuntimeError(f"Job failed: {status_resp.json()}")

        time.sleep(5)

    # 3. Fetch predictions
    pred_resp = requests.get(f"{BATCH_URL}/{job_id}/predictions", headers=HEADERS)
    return pred_resp.json()


def save_json(results):
    import os
    os.makedirs("results", exist_ok=True)
    with open("results/output.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Saved → results/output.json")

