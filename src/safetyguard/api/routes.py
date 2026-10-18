"""FastAPI REST routes for video analysis, job status, results, and exports."""

import io
import mimetypes
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Query, BackgroundTasks, status
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, HttpUrl

from safetyguard.config import (
    VIDEOS_DIR,
    OUTPUTS_DIR,
    MAX_UPLOAD_SIZE_MB,
    SUPPORTED_VIDEO_EXTENSIONS,
)
from safetyguard.jobs.manager import job_manager, JobStatus
from safetyguard.ml.evaluation import run_full_pipeline_evaluation
from safetyguard.video.youtube import YouTubeExtractionError, YouTubeVideoUnavailableError

router = APIRouter()


class YouTubeAnalyzeRequest(BaseModel):
    url: str


class URLAnalyzeRequest(BaseModel):
    url: str


class SampleAnalyzeRequest(BaseModel):
    sample_id: str


class IncidentReviewUpdate(BaseModel):
    incident_id: str
    review_status: str  # e.g., "Confirmed Potential Incident", "False Positive / Safe Activity", "Needs Senior Review"
    human_notes: Optional[str] = ""


@router.get("/health")
def health_check() -> Dict[str, Any]:
    """Health check endpoint confirming API service and environment readiness."""
    return {
        "status": "healthy",
        "service": "AI SafetyGuard API",
        "version": "1.0.0",
        "models_ready": True,
        "disclaimer": "Potential safety screening tool. Outputs require human review.",
    }


@router.get("/stats")
def get_dashboard_stats() -> Dict[str, Any]:
    """Return dashboard analytics based on real execution data."""
    all_jobs = job_manager.list_jobs(limit=100)
    total_analyzed = sum(1 for j in all_jobs if j["status"] == JobStatus.COMPLETED)
    running_jobs = sum(1 for j in all_jobs if j["status"] in [JobStatus.PROCESSING, JobStatus.QUEUED])
    total_incidents = sum(j.get("incident_count", 0) for j in all_jobs)
    high_priority_incidents = sum(j.get("high_priority_count", 0) for j in all_jobs)

    return {
        "total_videos_analyzed": total_analyzed,
        "running_jobs": running_jobs,
        "total_incidents_flagged": total_incidents,
        "high_priority_incidents": high_priority_incidents,
        "recent_jobs": all_jobs[:10],
    }


@router.post("/analyze/upload", status_code=status.HTTP_202_ACCEPTED)
async def analyze_video_upload(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Accept an uploaded video file, validate its size/type, and queue analysis.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    # Sanitize filename
    safe_name = os.path.basename(file.filename)
    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', safe_name)
    ext = Path(safe_name).suffix.lower()

    if ext not in SUPPORTED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}",
        )

    target_path = VIDEOS_DIR / f"upload_{safe_name}"

    # Save uploaded file with chunked streaming and size enforcement
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_bytes = 0

    try:
        with open(target_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    target_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum allowed upload size of {MAX_UPLOAD_SIZE_MB}MB.",
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as err:
        target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {err}")

    job_id = job_manager.create_job(job_type="upload", source_path_or_url=str(target_path))
    job_manager.start_analysis_job(job_id)

    return {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "message": "Video uploaded and analysis queued.",
        "filename": safe_name,
    }


SAMPLE_BENCHMARKS = {
    "brawl": {
        "id": "brawl",
        "title": "Subway Altercation & Brawl",
        "filename": "cctv_crime_altercation_brawl.mp4",
        "category": "Violent Conflict",
        "severity": "HIGH",
        "description": "Rapid physical altercation in a transit corridor with high jerk and chaotic motion.",
        "expected_result": "High Severity Threat Flagged",
    },
    "fall": {
        "id": "fall",
        "title": "Escalator Slip & Fall Incident",
        "filename": "cctv_crime_slip_fall.mp4",
        "category": "Slip & Fall Hazard",
        "severity": "HIGH",
        "description": "Sudden vertical jerk followed by prolonged post-fall immobility.",
        "expected_result": "Fall Hazard Detected",
    },
    "patrol": {
        "id": "patrol",
        "title": "Hallway Security Patrol",
        "filename": "cctv_normal_hallway_patrol.mp4",
        "category": "Normal Patrol",
        "severity": "LOW",
        "description": "Routine security guard walking through a commercial corridor.",
        "expected_result": "Safe Baseline (0 False Alarms)",
    },
    "store": {
        "id": "store",
        "title": "Retail Store Counter",
        "filename": "cctv_normal_store_counter.mp4",
        "category": "Normal Commerce",
        "severity": "LOW",
        "description": "Standard customer interaction and transaction at a checkout desk.",
        "expected_result": "Safe Baseline (0 False Alarms)",
    },
}


@router.get("/samples")
def get_sample_videos() -> Dict[str, Any]:
    """Return available pre-loaded CCTV benchmark demo scenarios."""
    samples = []
    for s_id, s_info in SAMPLE_BENCHMARKS.items():
        video_path = VIDEOS_DIR / s_info["filename"]
        samples.append({
            **s_info,
            "available": video_path.is_file(),
            "size_kb": round(video_path.stat().st_size / 1024, 1) if video_path.is_file() else 0,
        })
    return {"samples": samples}


@router.post("/analyze/sample", status_code=status.HTTP_202_ACCEPTED)
def analyze_sample_video(req: SampleAnalyzeRequest) -> Dict[str, Any]:
    """
    Queue analysis for a bundled CCTV benchmark scenario.
    """
    sample_id = req.sample_id.strip().lower()
    if sample_id not in SAMPLE_BENCHMARKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown sample '{sample_id}'. Available: {list(SAMPLE_BENCHMARKS.keys())}",
        )

    sample = SAMPLE_BENCHMARKS[sample_id]
    video_path = VIDEOS_DIR / sample["filename"]
    if not video_path.is_file():
        raise HTTPException(status_code=404, detail=f"Sample video file '{sample['filename']}' not found on server.")

    job_id = job_manager.create_job(job_type="sample", source_path_or_url=str(video_path))
    job = job_manager.get_job(job_id)
    if job:
        job["video_title"] = sample["title"]
        job_manager._persist_job(job_id)

    job_manager.start_analysis_job(job_id)

    return {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "message": f"Sample benchmark '{sample['title']}' queued for analysis.",
        "sample": sample,
    }


@router.post("/analyze/url", status_code=status.HTTP_202_ACCEPTED)
def analyze_video_url(req: URLAnalyzeRequest) -> Dict[str, Any]:
    """
    Queue analysis from either a direct web video stream (MP4/WebM/etc) or YouTube URL.
    """
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Video URL cannot be empty.")

    if not url.startswith("http://") and not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    job_id = job_manager.create_job(job_type="url", source_path_or_url=url)
    job_manager.start_analysis_job(job_id)

    return {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "message": "Online video stream queued for analysis.",
        "url": url,
    }


@router.post("/analyze/youtube", status_code=status.HTTP_202_ACCEPTED)
def analyze_youtube_video(req: YouTubeAnalyzeRequest) -> Dict[str, Any]:
    """
    Backward-compatible YouTube endpoint that routes into the universal URL pipeline.
    """
    return analyze_video_url(URLAnalyzeRequest(url=req.url))


@router.get("/jobs")
def get_jobs(limit: int = Query(30, ge=1, le=100)) -> Dict[str, Any]:
    """Get recent analysis jobs."""
    return {"jobs": job_manager.list_jobs(limit=limit)}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get current status and progress of a specific job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return {
        "job_id": job["job_id"],
        "job_type": job["job_type"],
        "status": job["status"],
        "progress_pct": job["progress_pct"],
        "current_stage": job["current_stage"],
        "error": job.get("error"),
        "created_at": job["created_at"],
        "completed_at": job.get("completed_at"),
        "video_metadata": job.get("video_metadata", {}),
    }


@router.get("/results/{job_id}")
def get_job_results(job_id: str) -> Dict[str, Any]:
    """Get comprehensive results and incident timeline for a completed job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job["status"] == JobStatus.FAILED:
        return {
            "job_id": job_id,
            "status": "failed",
            "error": job.get("error", "Unknown error during analysis"),
        }

    if job["status"] != JobStatus.COMPLETED or not job.get("results"):
        return {
            "job_id": job_id,
            "status": job["status"],
            "progress_pct": job["progress_pct"],
            "current_stage": job["current_stage"],
            "results": None,
        }

    return {
        "job_id": job_id,
        "status": job["status"],
        "video_metadata": job.get("video_metadata", {}),
        "results": job["results"],
    }


@router.patch("/results/{job_id}/review")
def update_incident_review(job_id: str, payload: IncidentReviewUpdate) -> Dict[str, Any]:
    """Update human review status and notes for an incident."""
    job = job_manager.get_job(job_id)
    if not job or not job.get("results"):
        raise HTTPException(status_code=404, detail="Job or results not found.")

    incidents = job["results"].get("incidents", [])
    updated = False

    for inc in incidents:
        if inc.get("incident_id") == payload.incident_id:
            inc["review_status"] = payload.review_status
            if payload.human_notes:
                inc["human_notes"] = payload.human_notes
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail=f"Incident '{payload.incident_id}' not found.")

    job_manager._persist_job(job_id)
    return {"status": "success", "message": "Review status updated.", "incident_id": payload.incident_id}


@router.get("/results/{job_id}/export")
def export_job_results(job_id: str, format: str = Query("json", pattern="^(json|csv)$")):
    """Export analysis results in JSON or CSV format."""
    job = job_manager.get_job(job_id)
    if not job or not job.get("results"):
        raise HTTPException(status_code=404, detail="Results not found for export.")

    results = job["results"]

    if format == "json":
        import json
        content = json.dumps(results, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={job_id}_report.json"},
        )
    else:
        # CSV export of incidents and timeline
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Incident_ID", "Start_Seconds", "End_Seconds", "Category", "Severity",
            "Confidence", "Reasons", "Distress_Keywords", "Review_Status", "Human_Notes"
        ])

        for inc in results.get("incidents", []):
            writer.writerow([
                inc.get("incident_id"),
                inc.get("start_seconds"),
                inc.get("end_seconds"),
                inc.get("category"),
                inc.get("severity"),
                inc.get("peak_confidence"),
                "; ".join(inc.get("reasons", [])),
                "; ".join(inc.get("keywords", [])),
                inc.get("review_status"),
                inc.get("human_notes", ""),
            ])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={job_id}_incidents.csv"},
        )


@router.get("/media/video/{filename}")
def stream_video(filename: str):
    """
    Stream video with safe path checking.
    """
    safe_name = os.path.basename(filename)
    video_path = VIDEOS_DIR / safe_name

    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video file not found.")

    mime_type, _ = mimetypes.guess_type(str(video_path))
    mime_type = mime_type or "video/mp4"

    def iterfile():
        with open(video_path, mode="rb") as file_like:
            yield from file_like

    file_size = video_path.stat().st_size
    return StreamingResponse(
        iterfile(),
        media_type=mime_type,
        headers={"Content-Length": str(file_size), "Accept-Ranges": "bytes"}
    )


@router.get("/ml/evaluation")
def get_ml_evaluation() -> Dict[str, Any]:
    """Run model evaluation on grouped benchmark dataset and return verified metrics."""
    return run_full_pipeline_evaluation()
