import cv2
import numpy as np
from pathlib import Path

# Find our project's video folder
video_folder = Path(__file__).resolve().parent.parent / "data" / "videos"
video_folder.mkdir(parents=True, exist_ok=True)

# Video settings
width = 640
height = 360
fps = 20
duration = 5
total_frames = fps * duration

# Try creating an MP4 video first
video_path = video_folder / "test_walk.mp4"
fourcc = cv2.VideoWriter_fourcc(*"mp4v")

writer = cv2.VideoWriter(
    str(video_path), fourcc, fps, (width, height)
)

# If MP4 is unavailable, try AVI
if not writer.isOpened():
    writer.release()
    video_path = video_folder / "test_walk.avi"
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")

    writer = cv2.VideoWriter(
        str(video_path), fourcc, fps, (width, height)
    )

if not writer.isOpened():
    raise RuntimeError("Could not create the video file.")

# Generate each frame
for i in range(total_frames):

    # Light background
    frame = np.full(
        (height, width, 3), 235, dtype=np.uint8
    )

    # Draw the ground
    cv2.line(frame, (0, 280), (width, 280), (80, 80, 80), 2)

    # Move the stick figure from left to right
    x = 40 + int(560 * i / total_frames)

    # Animate the walking movement
    step = np.sin(i * 2 * np.pi / 12)
    bob = int(3 * abs(step))

    head = (x, 115 + bob)
    shoulder = (x, 150 + bob)
    hip = (x, 205 + bob)

    # Head, body, arms and legs
    cv2.circle(frame, head, 17, (0, 100, 220), -1)
    cv2.line(frame, shoulder, hip, (0, 100, 220), 5)

    cv2.line(
        frame, shoulder,
        (x - int(25 * step), 180 + bob),
        (0, 100, 220), 4
    )

    cv2.line(
        frame, shoulder,
        (x + int(25 * step), 180 + bob),
        (0, 100, 220), 4
    )

    cv2.line(
        frame, hip,
        (x - int(18 * step), 250 + bob),
        (0, 100, 220), 4
    )

    cv2.line(
        frame, hip,
        (x + int(18 * step), 250 + bob),
        (0, 100, 220), 4
    )

    # Display information
    cv2.putText(
        frame,
        "SYNTHETIC WALKING VIDEO",
        (15, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (30, 30, 30),
        2
    )

    writer.write(frame)

writer.release()

print("Test video created successfully!")
print("Saved at:", video_path)
print("Duration:", duration, "seconds")
print("Frames:", total_frames)