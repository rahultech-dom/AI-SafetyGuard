from pathlib import Path
import subprocess
import yt_dlp

# Locate the project folders
project_folder = Path(__file__).resolve().parent.parent
audio_folder = project_folder / "data" / "audio"
audio_folder.mkdir(parents=True, exist_ok=True)

# Ask for a YouTube link
url = input("Paste your YouTube video link: ").strip()

if not url:
    raise SystemExit("Please provide a YouTube URL.")

# Download audio from the video
options = {
    "js_runtimes": {"node": {}},
    "format": "bestaudio/best",
    "outtmpl": str(
        audio_folder / "%(title).80s_%(id)s.%(ext)s"
    ),
    "noplaylist": True,
}

try:
    print("\nDownloading audio...")

    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=True)

        requested = info.get("requested_downloads") or []
        downloaded_path = (
            requested[0].get("filepath")
            if requested else None
        )

        if not downloaded_path:
            downloaded_path = downloader.prepare_filename(info)

    audio_file = Path(downloaded_path)

    if not audio_file.is_file():
        raise FileNotFoundError(
            f"Downloaded audio not found: {audio_file}"
        )

    print("Audio downloaded successfully!")
    print("Title:", info.get("title", "Unknown"))

    # Create a WAV file suitable for speech recognition
    wav_file = audio_folder / f"{audio_file.stem}.wav"

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(audio_file),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(wav_file),
    ]

    subprocess.run(command, check=True)

    print("\nAudio conversion successful!")
    print("WAV file saved at:", wav_file)
    print("Sample rate: 16000 Hz")
    print("Audio channels: Mono")

except Exception as error:
    print("\nAudio processing failed.")
    print("Reason:", error)