DEEPFACE IMPLEMENTATION

**Project structure** 

youtube_emotion_analyser/
│
├── app.py                  # Entry point — run this
├── youtube_downloader.py   # Downloads YouTube video via yt-dlp
├── hume_client.py          # DeepFace analysis logic
├── results/
│   └── output.json         # Analysis results saved here
├── downloads/              # Downloaded videos saved here
└── requirements.txt

**HOW DEEPFACE WORKS**
Frame (image)
    ↓
Face Detection       ← finds face bounding box (OpenCV / MTCNN / RetinaFace)
    ↓
Face Alignment       ← normalises face position and size
    ↓
Emotion Model        ← mini-Xception CNN trained on FER-2013 dataset
    ↓
7 emotion scores     ← softmax probabilities summing to 1.0

**INSTALLATION**
**
# 1. Clone or download the project
cd youtube_emotion_analyser

# 2. (Recommended) Create a virtual environment
conda create -n emotion-env python=3.10
conda activate emotion-env

# 3. Install dependencies
pip install -r requirements.txt
**

**RUN**
****
python app.py
****

Enter the Youtube URL 

**OUTPUT**
[
  {
    "timestamp_sec": 0.0,
    "dominant_emotion": "happy",
    "emotions": {
      "angry":    0.02,
      "disgust":  0.00,
      "fear":     0.01,
      "happy":    0.91,
      "sad":      0.01,
      "surprise": 0.03,
      "neutral":  0.02
    }
  },
  {
    "timestamp_sec": 1.0,
    "dominant_emotion": "neutral",
    "emotions": { ... }
  }
]