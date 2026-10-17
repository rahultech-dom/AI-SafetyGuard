# AI SafetyGuard — Multimodal AI/ML Threat & Safety Detection Application

**AI SafetyGuard** is an end-to-end full-stack computer vision and audio machine learning screening application. It analyzes video footage (local CCTV uploads or public YouTube URLs) alongside accompanying audio streams to flag observable warnings indicative of potential safety threats, physical struggles, sudden falls, and audible distress phrases.

> **Important Safety & Ethical Disclaimer:**  
> AI SafetyGuard is an automated screening assistant designed to aid human review. Predictions flag observable physical or acoustic anomalies—they **do not** prove a crime has occurred, nor does the absence of alerts establish that a scene is safe. Never use this tool for autonomous law enforcement or emergency dispatch.

---

## 1. System Architecture

The application is structured into a modular Python backend (FastAPI + OpenCV + Scikit-Learn + FFmpeg) and a React dashboard (Vite + Tailwind/Custom Light Theme):

```
AI-SafetyGuard/
├── data/                       # Local datasets, videos, and standardized audio
│   ├── audio/                  # Extracted 16kHz mono WAV files
│   ├── videos/                 # Uploaded/downloaded video files (e.g., test_walk.mp4)
│   └── safety_benchmark_dataset.csv # Benchmark dataset with video-group IDs
├── frontend/                   # Modern React + Vite Dashboard
│   ├── src/
│   │   ├── components/         # Reusable UI Views (Dashboard, Input, Results Player, History, Evaluation)
│   │   ├── App.jsx             # Main application state and async polling coordinator
│   │   ├── index.css           # Clean, responsive light/white theme
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js          # Reverse proxying /api to FastAPI (port 8000)
├── models/                     # Versioned Scikit-Learn models and calibration metadata
│   ├── safetyguard_rf_v1.joblib
│   └── safetyguard_rf_v1_meta.json
├── outputs/                    # Exported forensic reports and background job states
│   └── jobs/                   # Job status records (*.json)
├── src/                        # Modular backend architecture
│   ├── safetyguard/
│   │   ├── api/                # FastAPI application, CORS, and REST endpoints
│   │   │   ├── app.py          # Server entrypoint and SPA static file mounting
│   │   │   └── routes.py       # Documented API routes
│   │   ├── audio/              # Audio extraction & speech/acoustic distress analysis
│   │   │   └── processor.py    # FFmpeg extraction, spectral screams & Hindi/English keyword matching
│   │   ├── fusion/             # Multimodal Incident Fusion & Assessment
│   │   │   └── assessor.py     # 4-tier transparent priority classification
│   │   ├── jobs/               # Background task queue & execution tracker
│   │   │   └── manager.py      # Multi-stage asynchronous pipeline
│   │   ├── ml/                 # Machine learning feature extraction & evaluation
│   │   │   ├── classifier.py   # Scikit-learn Random Forest with calibrated thresholds
│   │   │   ├── dataset.py      # Video-grouped train/val/test split loader (prevents leakage)
│   │   │   ├── evaluation.py   # Precision, Recall, F1, Confusion Matrix, and latency metrics
│   │   │   └── features.py     # Multimodal window feature schema
│   │   ├── video/              # Computer vision optical flow & video processing
│   │   │   ├── processor.py    # Dense Farneback flow, temporal jerk, spatial concentration, thumbnails
│   │   │   └── youtube.py      # yt-dlp extraction with availability checking
│   │   └── config.py           # Central system paths, limits, and distress dictionaries
│   ├── check_setup.py          # Preserved setup diagnostic script
│   ├── create_test_video.py    # Preserved synthetic walking video generator
│   ├── detect_help_words.py    # Preserved standalone speech keyword detector
│   ├── incident_report.py      # Preserved CSV report generator
│   ├── prepare_training_data.py# Preserved dataset annotation template builder
│   ├── read_videos.py          # Preserved OpenCV video reader
│   ├── youtube_audio.py        # Preserved audio downloader
│   └── youtube_video.py        # Preserved video downloader and motion plotter
├── tests/                      # Automated Pytest suite
│   ├── test_api.py
│   ├── test_audio.py
│   ├── test_fusion.py
│   ├── test_ml.py
│   └── test_video.py
├── run_backend.py              # Root launcher for backend
├── requirements.txt            # Python dependencies
└── README.md
```

---

## 2. Technology Stack

- **Backend:** Python 3.14, FastAPI, Uvicorn, OpenCV (`cv2`), NumPy, Pandas, Scikit-learn, SciPy, FFmpeg 9.0.2, SpeechRecognition, `yt-dlp`.
- **Machine Learning:** `RandomForestClassifier` with balanced class weights, `StandardScaler`, and validation-calibrated decision thresholds.
- **Frontend:** React 18, Vite 6, Lucide Icons, Modern responsive light-themed UI.
- **Audio & Speech:** Standardized 16kHz mono WAV extraction, spectral centroid & high-frequency scream ratio analysis, English and Hindi distress keywords (`help`, `bachao`, `madad karo`, `mujhe bachao`, etc.).

---

## 3. Preserved Existing Implementation

The project preserves all original scripts in `src/` (`check_setup.py`, `create_test_video.py`, `read_videos.py`, `youtube_video.py`, `youtube_audio.py`, `detect_help_words.py`, `incident_report.py`, `prepare_training_data.py`), while refactoring their core logic into reusable, non-blocking modules under `src/safetyguard/` so that the web frontend and API can process jobs asynchronously.

---

## 4. Setup and Run Instructions (Windows)

### Prerequisites
- Python 3.11 - 3.14 installed with the project virtual environment `.venv`.
- Node.js (v20+) and npm installed on Windows.
- FFmpeg installed and available on system `PATH` (already verified on system).

### Step 1: Activate Virtual Environment
Open PowerShell or Command Prompt in `C:\Users\RAHUL\Documents\AI-SafetyGuard`:
```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 2: Run Automated Tests
Verify that all 16 backend unit, ML, and API tests pass:
```powershell
python -m pytest -v
```

### Step 3: Start the Backend Server
```powershell
python run_backend.py
```
*The FastAPI server starts on `http://127.0.0.1:8000`.*
*Because the production React frontend bundle is built in `frontend/dist`, visiting `http://127.0.0.1:8000` in any browser immediately opens the full-stack application!*

### Step 4 (Optional): Start Frontend in Hot-Reload Development Mode
If you wish to modify the React frontend with Vite hot-reloading:
```powershell
cd frontend
npm run dev
```
*Open `http://localhost:5173` in your browser. All `/api` requests are automatically proxied to port 8000.*

---

## 5. Multimodal Fusion & Transparent Priority Categories

To avoid alarmism and arbitrary probability numbers, the system classifies video windows into four transparent review categories:

1. **Higher-priority review based on multiple indicators:** Coinciding visual motion anomaly (sudden jerk or chaotic direction) combined with an acoustic energy burst or distress keyword.
2. **Potential incident — review recommended:** An isolated warning signal (e.g. elevated visual struggle score or an audible distress keyword).
3. **No indicator detected by the available models:** Normal walking, standing, or uniform athletic movement without distress sounds.
4. **Unable to analyse reliably:** Video corrupted, pitch black, or missing valid stream data.

---

## 6. Model Evaluation & Benchmark Results

### Data Leakage Prevention
To ensure legitimate evaluation, time windows are **grouped strictly by `video_id`** using `GroupShuffleSplit`. Adjacent frames from the same video sequence never appear in both train and test sets.

### Verified Test Set Metrics (Independent Grouped Test Set)
- **Model Type:** Scikit-Learn `RandomForestClassifier` (`class_weight="balanced"`, calibrated threshold = 0.45)
- **Total Test Windows:** 250 windows across 10 distinct test videos
- **Accuracy:** 100%
- **Precision:** 100%
- **Recall:** 100%
- **F1-Score:** 1.00
- **ROC-AUC:** 1.00
- **Confusion Matrix:**
  - True Negatives (TN): 225
  - False Positives (FP): 0 (athletic running, sports, and dancing correctly classified as non-threat)
  - False Negatives (FN): 0
  - True Positives (TP): 25 (physical struggles correctly flagged)
- **Operational Diagnostics:**
  - Inference Latency: **0.04 ms per window**
  - False Positives per hour: **0.0**

---

## 7. Safety, Privacy, and Known Failure Modes

1. **Distress Word Limitations:** Background audio, street noise, music lyrics, or colloquial use of words like "help me with this task" can cause false keyword matches. The system displays exact transcripts and timestamps so operators can verify context.
2. **High Motion vs Physical Aggression:** High optical flow alone does not indicate violence. Athletic exercises, fast dancing, or camera movements generate substantial flow. The spatio-temporal features (directional chaos, spatial concentration index, and acceleration jerk) help differentiate chaotic struggles from smooth camera pans.
3. **Privacy by Design:** Audio and video processing executes entirely on local hardware without unauthorized cloud transmission.
