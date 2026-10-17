import cv2
from pathlib import Path

# Find the video inside our project
project_folder = Path(__file__).resolve().parent.parent
video_path = project_folder / "data" / "videos" / "test_walk.mp4"

# Open the video
cap = cv2.VideoCapture(str(video_path))

if not cap.isOpened():
    raise SystemExit("Error: Could not open the video.")

# Get basic video information
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print("Video opened successfully!")
print("Frames reported:", total_frames)
print("Frames per second:", fps)
print("Resolution:", width, "x", height)

frames_read = 0

try:
    while True:
        # Read the next frame
        success, frame = cap.read()

        # Stop when there are no more frames
        if not success:
            break

        frames_read += 1

        # Display the current frame number
        cv2.putText(
            frame,
            f"Frame: {frames_read}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

        # Show the frame in a window
        cv2.imshow("AI SafetyGuard - Video Reader", frame)

        # Wait according to the video's frame rate
        delay = max(1, int(1000 / fps)) if fps > 0 else 30
        key = cv2.waitKey(delay) & 0xFF

        # Press Q to stop playback
        if key == ord("q"):
            print("Playback stopped by user.")
            break

finally:
    cap.release()
    cv2.destroyAllWindows()

print("Frames successfully read:", frames_read)
print("Video processing finished.")