from pathlib import Path
import cv2
import yt_dlp
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
# Locate our project's video folder
project_folder = Path(__file__).resolve().parent.parent
video_folder = project_folder / "data" / "videos"
video_folder.mkdir(parents=True, exist_ok=True)

# Ask for a YouTube URL
url = input("Paste your YouTube video link: ").strip()

if not url:
    raise SystemExit("No URL entered.")

# Download settings
options = {
    # Enable JavaScript support through Node.js
    "js_runtimes": {"node": {}},

    # Download video and audio separately when necessary
    "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",

    # Combine the streams into an MP4 file
    "merge_output_format": "mp4",

    # Save files in the project video folder
    "outtmpl": str(
        video_folder / "%(title).80s_%(id)s.%(ext)s"
    ),

    # Do not download an entire playlist
    "noplaylist": True,
}

try:
    print("\nRetrieving video. Please wait...")

    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=True)
        downloaded_file = Path(downloader.prepare_filename(info))

    if not downloaded_file.is_file():
        raise FileNotFoundError(
            "Downloaded video file could not be located."
        )

    print("\nVideo downloaded successfully!")
    print("Title:", info.get("title", "Unknown"))
    print("Saved at:", downloaded_file)

except Exception as error:
    print("\nCould not retrieve this YouTube video.")
    print("Reason:", error)
    raise SystemExit(1)

# Open the downloaded video with OpenCV
cap = cv2.VideoCapture(str(downloaded_file))

if not cap.isOpened():
    cap.release()
    raise SystemExit(
        "The video was downloaded, but OpenCV could not open it."
    )

fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

print("\nVideo opened successfully!")
print("Frames:", total_frames)
print("FPS:", fps)


frames_read = 0
motion_scores = []
timestamps = []
previous_gray = None

try:
    while True:
        success, frame = cap.read()

        if not success:
            break

        frames_read += 1

        # Resize frames to make calculations faster
        small_frame = cv2.resize(frame, (320, 180))

        # Convert the frame to grayscale
        gray = cv2.cvtColor(
            small_frame, cv2.COLOR_BGR2GRAY
        )

        # Compare this frame with the previous frame
        if previous_gray is not None:

            flow = cv2.calcOpticalFlowFarneback(
                previous_gray,
                gray,
                None,
                0.5,
                3,
                15,
                3,
                5,
                1.2,
                0
            )

            # Calculate movement magnitude
            magnitude, _ = cv2.cartToPolar(
                flow[..., 0],
                flow[..., 1]
            )

            motion_score = float(np.mean(magnitude))

            motion_scores.append(motion_score)

            time_seconds = (
                frames_read / fps if fps > 0
                else frames_read
            )

            timestamps.append(time_seconds)

            cv2.putText(
                frame,
                f"Motion: {motion_score:.2f}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

        previous_gray = gray

        cv2.imshow(
            "AI SafetyGuard - Motion Analysis", frame
        )

        delay = (
            max(1, int(1000 / fps))
            if fps > 0 else 30
        )

        if cv2.waitKey(delay) & 0xFF == ord("q"):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()

print("\nVideo analysis complete.")
print("Frames processed:", frames_read)

if motion_scores:
    print(
        "Average motion intensity:",
        round(float(np.mean(motion_scores)), 3)
    )
        # Store movement measurements in a DataFrame
    features_df = pd.DataFrame({
        "time_seconds": timestamps,
        "motion_intensity": motion_scores
    })

    # Save the dataset inside the outputs folder
    output_folder = project_folder / "outputs"
    output_folder.mkdir(parents=True, exist_ok=True)

    csv_path = (
        output_folder /
        f"{downloaded_file.stem}_motion_features.csv"
    )

    features_df.to_csv(csv_path, index=False)
    
    # Divide motion measurements into 1-second windows
    window_features = (
        features_df.assign(
            window_start_seconds=np.floor(
                features_df["time_seconds"]
            ).astype(int)
        )
        .groupby("window_start_seconds", as_index=False)
        .agg(
            motion_mean=("motion_intensity", "mean"),
            motion_std=("motion_intensity", "std"),
            motion_max=("motion_intensity", "max"),
            motion_min=("motion_intensity", "min"),
        )
        .fillna(0)
    )

    # Save the window-level dataset
    window_path = (
        output_folder /
        f"{downloaded_file.stem}_window_features.csv"
    )

    window_features.to_csv(window_path, index=False)

    print("Window features saved to:", window_path)

    print("Motion features saved to:", csv_path)
    # Plot movement over time
    plt.figure(figsize=(10, 4))
    plt.plot(timestamps, motion_scores)

    plt.title("Video Motion Intensity Over Time")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Average optical flow magnitude")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
else:
    print("Not enough frames to calculate motion.")


try:
    while True:
        success, frame = cap.read()

        if not success:
            break

        frames_read += 1

        cv2.putText(
            frame,
            f"Frame: {frames_read}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

        cv2.imshow("AI SafetyGuard - YouTube Video", frame)

        delay = max(1, int(1000 / fps)) if fps > 0 else 30

        if cv2.waitKey(delay) & 0xFF == ord("q"):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()

print("\nFrames processed:", frames_read)
print("Processing finished.")