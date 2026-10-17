"""Background analysis job runner and progress manager."""

import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd

from safetyguard.config import JOBS_DIR, OUTPUTS_DIR
from safetyguard.video.processor import extract_video_features
from safetyguard.video.youtube import download_youtube_video
from safetyguard.audio.processor import (
    extract_audio_from_video,
    compute_acoustic_features,
    transcribe_and_detect_distress,
)
from safetyguard.ml.features import assemble_multimodal_features
from safetyguard.ml.classifier import get_default_classifier
from safetyguard.fusion.assessor import assess_multimodal_incidents

logger = logging.getLogger(__name__)


class JobStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisJobManager:
    """Manages asynchronous video analysis jobs with stage tracking and persistence."""

    def __init__(self, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="SafetyGuardWorker")
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load_persisted_jobs()

    def _load_persisted_jobs(self) -> None:
        """Load recent jobs from disk to populate history across server reboots."""
        try:
            for job_file in sorted(JOBS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]:
                with open(job_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    job_id = data.get("job_id")
                    if job_id:
                        self._jobs[job_id] = data
        except Exception as err:
            logger.warning("Error loading persisted jobs: %s", err)

    def _persist_job(self, job_id: str) -> None:
        """Persist job state to JSON file."""
        job_data = self._jobs.get(job_id)
        if not job_data:
            return
        job_file = JOBS_DIR / f"{job_id}.json"
        try:
            with open(job_file, "w", encoding="utf-8") as f:
                json.dump(job_data, f, indent=2)
        except Exception as err:
            logger.warning("Error persisting job %s: %s", job_id, err)

    def create_job(self, job_type: str, source_path_or_url: str) -> str:
        """Create and register a new queued job."""
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "job_type": job_type,  # 'upload' or 'youtube'
                "source": source_path_or_url,
                "status": JobStatus.QUEUED,
                "progress_pct": 0.0,
                "current_stage": "Queued for processing",
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "error": None,
                "video_metadata": {},
                "results": None,
            }
            self._persist_job(job_id)
        return job_id

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress_pct: Optional[float] = None,
        current_stage: Optional[str] = None,
        error: Optional[str] = None,
        results: Optional[Dict[str, Any]] = None,
        video_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return

            if status:
                job["status"] = status
                if status == JobStatus.PROCESSING and not job.get("started_at"):
                    job["started_at"] = datetime.now().isoformat()
                elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                    job["completed_at"] = datetime.now().isoformat()

            if progress_pct is not None:
                job["progress_pct"] = round(progress_pct, 1)
            if current_stage is not None:
                job["current_stage"] = current_stage
            if error is not None:
                job["error"] = error
            if results is not None:
                job["results"] = results
            if video_metadata is not None:
                job["video_metadata"] = video_metadata

            self._persist_job(job_id)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            # Sort by created_at descending
            sorted_jobs = sorted(
                self._jobs.values(),
                key=lambda j: j.get("created_at", ""),
                reverse=True,
            )
            # Return summary without large result payload for performance
            summaries = []
            for j in sorted_jobs[:limit]:
                res = j.get("results") or {}
                summary = res.get("summary") or {}
                summaries.append({
                    "job_id": j["job_id"],
                    "job_type": j["job_type"],
                    "source": Path(j.get("source", "")).name if j["job_type"] == "upload" else j.get("source", ""),
                    "status": j["status"],
                    "progress_pct": j.get("progress_pct", 0.0),
                    "current_stage": j.get("current_stage", ""),
                    "created_at": j["created_at"],
                    "completed_at": j.get("completed_at"),
                    "incident_count": summary.get("incident_count", 0),
                    "high_priority_count": summary.get("high_priority_count", 0),
                    "video_title": j.get("video_metadata", {}).get("filename", ""),
                    "duration": j.get("video_metadata", {}).get("duration", 0.0),
                })
            return summaries

    def start_analysis_job(self, job_id: str) -> None:
        """Submit job to the thread pool for background execution."""
        self.executor.submit(self._run_job_pipeline, job_id)

    def _run_job_pipeline(self, job_id: str) -> None:
        """Execute end-to-end analysis stages in the background thread."""
        job = self.get_job(job_id)
        if not job:
            return

        try:
            self.update_job(job_id, status=JobStatus.PROCESSING, progress_pct=5.0, current_stage="Initializing job")

            # Stage 1: Obtain video file
            job_type = job["job_type"]
            source = job["source"]

            if job_type == "youtube":
                self.update_job(job_id, progress_pct=10.0, current_stage="Retrieving YouTube video with yt-dlp")
                yt_info = download_youtube_video(source)
                video_file = Path(yt_info["video_path"])
                title = yt_info.get("title", video_file.name)
            else:
                video_file = Path(source)
                title = video_file.name

            if not video_file.is_file():
                raise FileNotFoundError(f"Video file not found: {video_file}")

            # Stage 2: Video Preprocessing & Spatio-Temporal Motion Analysis
            self.update_job(job_id, progress_pct=25.0, current_stage="Extracting video optical flow & temporal jerk")

            def video_progress(pct: float, msg: str):
                overall_pct = 25.0 + (pct * 0.35)  # 25% -> 60%
                self.update_job(job_id, progress_pct=overall_pct, current_stage=msg)

            video_df, meta = extract_video_features(video_file, progress_callback=video_progress)
            meta["title"] = title
            self.update_job(job_id, video_metadata=meta)

            # Stage 3: Audio Extraction & Acoustic/Speech Analysis
            self.update_job(job_id, progress_pct=60.0, current_stage="Extracting audio track via FFmpeg")
            wav_file = extract_audio_from_video(video_file)

            audio_df = pd.DataFrame()
            transcripts = []
            alerts = []

            if wav_file is not None:
                self.update_job(job_id, progress_pct=65.0, current_stage="Computing acoustic features and scream detection")
                audio_df = compute_acoustic_features(wav_file)

                self.update_job(job_id, progress_pct=72.0, current_stage="Transcribing speech & detecting distress keywords")

                def audio_progress(pct: float, msg: str):
                    overall_pct = 72.0 + (pct * 0.13)  # 72% -> 85%
                    self.update_job(job_id, progress_pct=overall_pct, current_stage=msg)

                transcripts, alerts = transcribe_and_detect_distress(
                    wav_file,
                    progress_callback=audio_progress,
                )
            else:
                self.update_job(job_id, progress_pct=85.0, current_stage="No audio stream found; continuing visual analysis")

            # Stage 4: Feature Assembly & Scikit-Learn Threat Inference
            self.update_job(job_id, progress_pct=87.0, current_stage="Assembling multimodal features and running ML inference")
            feature_df = assemble_multimodal_features(video_df, audio_df, alerts)

            # Run ML model inference
            try:
                clf = get_default_classifier()
                inference_df = clf.predict_dataframe(feature_df)
            except Exception as ml_err:
                logger.warning("ML inference fallback used: %s", ml_err)
                inference_df = feature_df.copy()
                inference_df["model_threat_probability"] = 0.0

            # Stage 5: Multimodal Incident Assessment & Fusion
            self.update_job(job_id, progress_pct=95.0, current_stage="Assessing multimodal incident intervals")
            assessment = assess_multimodal_incidents(
                inference_df,
                transcripts=transcripts,
                distress_alerts=alerts,
            )

            # Stage 6: Completion
            final_results = {
                "job_id": job_id,
                "video_file": str(video_file.name),
                "summary": assessment["summary"],
                "incidents": assessment["incidents"],
                "timeline_windows": assessment["timeline_windows"],
                "transcripts": transcripts,
                "distress_alerts": alerts,
                "completed_at": datetime.now().isoformat(),
            }

            self.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress_pct=100.0,
                current_stage="Analysis completed successfully",
                results=final_results,
            )

        except Exception as err:
            logger.exception("Job %s failed: %s", job_id, err)
            self.update_job(
                job_id,
                status=JobStatus.FAILED,
                progress_pct=100.0,
                current_stage="Analysis failed",
                error=str(err),
            )


# Global job manager singleton
job_manager = AnalysisJobManager()
