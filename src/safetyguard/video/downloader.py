"""Universal video downloader supporting direct HTTP/HTTPS video URLs and YouTube fallback."""

import logging
import mimetypes
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import cv2

from safetyguard.config import VIDEOS_DIR, MAX_UPLOAD_SIZE_MB, SUPPORTED_VIDEO_EXTENSIONS
from safetyguard.video.youtube import download_youtube_video, YouTubeExtractionError, YouTubeVideoUnavailableError

logger = logging.getLogger(__name__)

YOUTUBE_DOMAINS = ["youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com"]


def is_youtube_url(url: str) -> bool:
    """Check if the provided URL points to YouTube."""
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        return any(d in netloc for d in YOUTUBE_DOMAINS)
    except Exception:
        return False


def sanitize_filename(name: str) -> str:
    """Sanitize string to be safe for filenames."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", name)
    cleaned = re.sub(r"\s+", "_", cleaned).strip()
    return cleaned[:80]


def get_video_info_from_file(file_path: Path) -> Dict[str, Any]:
    """Inspect local video file with OpenCV to extract duration, fps, resolution."""
    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        return {"duration": 0.0, "fps": 0.0, "width": 0, "height": 0}

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()

    duration = float(frame_count / fps) if fps > 0 else 0.0
    return {
        "duration": duration,
        "fps": fps,
        "width": width,
        "height": height,
        "frame_count": int(frame_count),
    }


def download_direct_video_stream(
    url: str,
    output_dir: Optional[Path] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Dict[str, Any]:
    """
    Download a video directly from an HTTP/HTTPS URL with streaming chunks and size limits.
    Works universally across cloud deployments (Render, AWS, GCP, local) without bot blocks.
    """
    clean_url = url.strip()
    target_dir = output_dir or VIDEOS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    # Determine default filename from URL path
    parsed = urllib.parse.urlparse(clean_url)
    raw_filename = os.path.basename(parsed.path) or "stream_video.mp4"
    safe_name = sanitize_filename(raw_filename)

    ext = Path(safe_name).suffix.lower()
    if ext not in SUPPORTED_VIDEO_EXTENSIONS:
        safe_name = f"{Path(safe_name).stem}.mp4"

    dest_path = target_dir / f"web_{safe_name}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }

    req = urllib.request.Request(clean_url, headers=headers)
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    try:
        if progress_callback:
            progress_callback(5.0, "Connecting to video server...")

        with urllib.request.urlopen(req, timeout=30) as response:
            total_size_header = response.headers.get("Content-Length")
            total_size = int(total_size_header) if total_size_header else 0

            if total_size > max_bytes:
                raise ValueError(
                    f"Remote video size ({total_size / (1024*1024):.1f}MB) exceeds {MAX_UPLOAD_SIZE_MB}MB limit."
                )

            downloaded_bytes = 0
            chunk_size = 512 * 1024  # 512 KB chunks

            with open(dest_path, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded_bytes += len(chunk)

                    if downloaded_bytes > max_bytes:
                        dest_path.unlink(missing_ok=True)
                        raise ValueError(f"Video download exceeded {MAX_UPLOAD_SIZE_MB}MB limit.")

                    if total_size > 0 and progress_callback:
                        pct = min(95.0, (downloaded_bytes / total_size) * 100.0)
                        progress_callback(pct, f"Downloading web stream ({downloaded_bytes / (1024*1024):.1f}MB)...")

        # Validate downloaded file with OpenCV
        meta = get_video_info_from_file(dest_path)
        if meta["duration"] <= 0:
            dest_path.unlink(missing_ok=True)
            raise ValueError("Downloaded file is not a valid or readable video stream.")

        if progress_callback:
            progress_callback(100.0, "Video downloaded successfully")

        return {
            "video_path": str(dest_path.resolve()),
            "title": safe_name,
            "duration": meta["duration"],
            "video_id": safe_name,
            "uploader": parsed.netloc,
        }

    except Exception as err:
        dest_path.unlink(missing_ok=True)
        logger.error("Failed to download direct video stream from %s: %s", clean_url, err)
        raise YouTubeExtractionError(f"Failed to retrieve video stream: {err}") from err


def download_any_video_url(
    url: str,
    output_dir: Optional[Path] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Dict[str, Any]:
    """
    Download video from either a YouTube URL or any direct web video URL.
    """
    clean_url = url.strip()
    if is_youtube_url(clean_url):
        logger.info("Detected YouTube URL: %s", clean_url)
        return download_youtube_video(clean_url, output_dir=output_dir)
    else:
        logger.info("Detected direct web video stream URL: %s", clean_url)
        return download_direct_video_stream(clean_url, output_dir=output_dir, progress_callback=progress_callback)
