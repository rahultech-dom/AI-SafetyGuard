"""Tests for FastAPI endpoints."""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from safetyguard.api.app import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["models_ready"] is True
    assert "disclaimer" in data


def test_stats_endpoint():
    """Verify stats dashboard endpoint."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_videos_analyzed" in data
    assert "running_jobs" in data
    assert "recent_jobs" in data


def test_jobs_list():
    """Verify jobs list endpoint."""
    response = client.get("/api/jobs")
    assert response.status_code == 200
    assert "jobs" in response.json()


def test_upload_invalid_file_extension():
    """Verify that uploading non-video file returns 400."""
    fake_file = ("script.exe", b"invalid executable bytes", "application/octet-stream")
    response = client.post("/api/analyze/upload", files={"file": fake_file})
    assert response.status_code == 400
    assert "Unsupported video format" in response.json()["detail"]


def test_youtube_invalid_url():
    """Verify that invalid YouTube URL returns 400."""
    response = client.post("/api/analyze/youtube", json={"url": "https://example.com/not-youtube"})
    assert response.status_code == 400
    assert "Invalid YouTube URL format" in response.json()["detail"]


def test_ml_evaluation_endpoint():
    """Verify that ML evaluation endpoint returns grouped metrics."""
    response = client.get("/api/ml/evaluation")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "confusion_matrix" in data
    assert "test_samples" in data
