
from pathlib import Path
import pandas as pd

# Locate project folders
project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "outputs"
data_folder = project_folder / "data"

# Find all one-second feature datasets
feature_files = sorted(
    output_folder.glob("*_window_features.csv")
)

if not feature_files:
    raise SystemExit(
        "No window feature files found. "
        "Process a video with youtube_video.py first."
    )

required_columns = [
    "window_start_seconds",
    "motion_mean",
    "motion_std",
    "motion_max",
    "motion_min",
]

all_datasets = []

for file_path in feature_files:
    df = pd.read_csv(file_path)

    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        print(f"Skipping {file_path.name}: missing {missing}")
        continue

    # Preserve which video each row belongs to
    df["video_id"] = file_path.name.removesuffix(
        "_window_features.csv"
    )

    all_datasets.append(df)

if not all_datasets:
    raise SystemExit("No valid feature datasets were found.")

# Combine available datasets
training_data = pd.concat(
    all_datasets,
    ignore_index=True
)

# Add blank labels for manual annotation
training_data["label"] = ""
training_data["notes"] = ""

columns = [
    "video_id",
    "window_start_seconds",
    "motion_mean",
    "motion_std",
    "motion_max",
    "motion_min",
    "label",
    "notes",
]

training_data = training_data[columns]

# Save the template without overwriting existing annotations
data_folder.mkdir(parents=True, exist_ok=True)

template_path = data_folder / "training_labels_template.csv"

if template_path.exists():
    raise SystemExit(
        f"{template_path.name} already exists. "
        "Rename or back up the existing file before "
        "creating a new template, so annotations aren't lost."
    )

training_data.to_csv(template_path, index=False)

print("Training template created!")
print("Rows:", len(training_data))
print("Distinct videos:", training_data["video_id"].nunique())
print("Saved to:", template_path)
print("\nLabels have intentionally been left blank.")
