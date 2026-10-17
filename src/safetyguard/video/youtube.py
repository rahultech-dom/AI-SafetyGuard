"""Safe YouTube video & audio extraction module."""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional
import yt_dlp

from safetyguard.config import VIDEOS_DIR, AUDIO_DIR

logger = logging.getLogger(__name__)


class YouTubeExtractionError(Exception):
    """Raised when YouTube video extraction fails."""
    pass


class YouTubeVideoUnavailableError(YouTubeExtractionError):
    """Raised when video is private, removed, or geo-restricted."""
    pass


def sanitize_filename(name: str) -> str:
    """Sanitize string to be safe for filenames across OS platforms."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:80]


def download_youtube_video(url: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Download a publicly accessible YouTube video using yt-dlp.
    
    Args:
        url: Public YouTube URL
        output_dir: Destination folder (defaults to VIDEOS_DIR)
        
    Returns:
        Dictionary containing:
            - video_path: Path to downloaded video file
            - title: Video title
            - duration: Video duration in seconds
            - video_id: YouTube video ID
            - uploader: Channel name
    """
    if not url or not url.strip():
        raise YouTubeExtractionError("No URL provided.")

    clean_url = url.strip()
    target_dir = output_dir or VIDEOS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    options: Dict[str, Any] = {
        "js_runtimes": {"node": {}},
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(target_dir / "%(title).80s_%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            # Extract info first without full download to check availability
            info = ydl.extract_info(clean_url, download=True)
            if info is None:
                raise YouTubeVideoUnavailableError("Could not retrieve video metadata.")

            downloaded_path = Path(ydl.prepare_filename(info))
            # If merged format was mp4, extension might have been updated
            if not downloaded_path.is_file():
                mp4_path = downloaded_path.with_suffix(".mp4")
                if mp4_path.is_file():
                    downloaded_path = mp4_path
                else:
                    # Look in directory for matching ID
                    matches = list(target_dir.glob(f"*{info.get('id')}*.mp4"))
                    if matches:
                        downloaded_path = matches[0]
                    else:
                        raise YouTubeExtractionError(f"Target video file not found after download: {downloaded_path}")

            return {
                "video_path": str(downloaded_path.resolve()),
                "title": info.get("title", "Unknown Title"),
                "duration": float(info.get("duration", 0.0) or 0.0),
                "video_id": str(info.get("id", "unknown")),
                "uploader": info.get("uploader", "Unknown"),
            }

    except yt_dlp.utils.DownloadError as err:
        err_msg = str(err)
        if any(term in err_msg.lower() for term in ["private", "copyright", "removed", "not available", "sign in"]):
            raise YouTubeVideoUnavailableError(f"Video unavailable or restricted: {err_msg}") from err
        raise YouTubeExtractionError(f"Failed to download YouTube video: {err_msg}") from err
    except Exception as err:
        raise YouTubeExtractionError(f"Unexpected error retrieving YouTube video: {err}") from err
