
from pathlib import Path
import pandas as pd

# Locate project folders
project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "outputs"

# Find previously generated one-second video features
feature_files = sorted(
    output_folder.glob("*_window_features.csv"),
    key=lambda path: path.stat().st_mtime,
    reverse=True
)

if not feature_files:
    raise SystemExit(
        "No window feature CSV found. Run youtube_video.py first."
    )

# Let the user choose which video features to analyse
print("Available video feature files:")

for index, file_path in enumerate(feature_files, start=1):
    print(f"{index}. {file_path.name}")

choice = input(
    "\nChoose a file number, or press Enter for the latest: "
).strip()

if choice:
    if not choice.isdigit() or not 1 <= int(choice) <= len(feature_files):
        raise SystemExit("Invalid selection.")

    feature_path = feature_files[int(choice) - 1]
else:
    feature_path = feature_files[0]

# Load the video features and audio alerts
motion_df = pd.read_csv(feature_path)
alerts_path = output_folder / "distress_alerts.csv"

if not alerts_path.is_file():
    raise SystemExit(
        "distress_alerts.csv not found. Run detect_help_words.py first."
    )

alerts_df = pd.read_csv(alerts_path)

# Check required video columns
required_columns = [
    "window_start_seconds",
    "motion_mean",
    "motion_std",
    "motion_max",
    "motion_min"
]

missing = [
    column for column in required_columns
    if column not in motion_df.columns
]

if missing:
    raise SystemExit(
        f"Video features are missing columns: {missing}"
    )

# Check the expected audio-alert columns
audio_columns = ["start_seconds", "end_seconds", "matched_phrases"]

if any(column not in alerts_df.columns for column in audio_columns):
    raise SystemExit(
        "The audio alert CSV has an unexpected format. "
        "Run detect_help_words.py again."
    )

# Convert timestamps to numerical values
motion_df["window_start_seconds"] = pd.to_numeric(
    motion_df["window_start_seconds"], errors="coerce"
)

alerts_df["start_seconds"] = pd.to_numeric(
    alerts_df["start_seconds"], errors="coerce"
)

alerts_df["end_seconds"] = pd.to_numeric(
    alerts_df["end_seconds"], errors="coerce"
)

motion_df = motion_df.dropna(subset=["window_start_seconds"])
alerts_df = alerts_df.dropna(
    subset=["start_seconds", "end_seconds"]
)

# Match audio-alert segments to video windows
report_rows = []

for _, motion in motion_df.iterrows():
    start = float(motion["window_start_seconds"])
    end = start + 1

    # Find audio-alert segments overlapping this video window
    matching_alerts = alerts_df[
        (alerts_df["start_seconds"] < end)
        & (alerts_df["end_seconds"] > start)
    ]

    phrases = [
        str(value)
        for value in matching_alerts["matched_phrases"].dropna()
        if str(value).strip()
    ]

    transcripts = []
    if "transcript" in matching_alerts.columns:
        transcripts = [
            str(value)
            for value in matching_alerts["transcript"].dropna()
            if str(value).strip()
        ]

    audio_segments = [
        f"{row['start_seconds']:g}-{row['end_seconds']:g}s"
        for _, row in matching_alerts.iterrows()
    ]

    row = motion.to_dict()
    row["audio_distress_detected"] = not matching_alerts.empty
    row["audio_segment_times"] = "; ".join(audio_segments)
    row["matched_phrases"] = "; ".join(sorted(set(phrases)))
    row["transcript"] = " | ".join(transcripts)

    if not matching_alerts.empty:
        row["review_status"] = "Human review recommended"
    else:
        row["review_status"] = (
            "No matched distress phrase; safety not established"
        )

    report_rows.append(row)

# Save the combined report
report_df = pd.DataFrame(report_rows)
report_path = output_folder / "incident_report.csv"

report_df.to_csv(report_path, index=False)

print("\nCombined report created successfully!")
print("Video features:", feature_path.name)
print("Audio alerts:", len(alerts_df))
print("Video time windows:", len(report_df))
print(
    "Windows overlapping audio alerts:",
    int(report_df["audio_distress_detected"].sum())
)
print("Saved to:", report_path)
print(
    "\nImportant: a motion measurement or matched phrase "
    "does not prove that a crime occurred."
)
