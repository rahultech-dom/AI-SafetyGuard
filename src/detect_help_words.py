
from pathlib import Path
import re
import pandas as pd
import speech_recognition as sr

# Locate project folders
project_folder = Path(__file__).resolve().parent.parent
audio_folder = project_folder / "data" / "audio"
output_folder = project_folder / "outputs"
output_folder.mkdir(parents=True, exist_ok=True)

# Find available WAV files
wav_files = sorted(
    audio_folder.glob("*.wav"),
    key=lambda path: path.stat().st_mtime,
    reverse=True
)

if not wav_files:
    raise SystemExit(
        "No WAV file found. Run youtube_audio.py first."
    )

print("Available audio files:")
for index, path in enumerate(wav_files, start=1):
    print(f"{index}. {path.name}")

choice = input(
    "\nEnter file number, or press Enter for the latest: "
).strip()

if choice:
    if not choice.isdigit() or not 1 <= int(choice) <= len(wav_files):
        raise SystemExit("Invalid file number.")
    audio_path = wav_files[int(choice) - 1]
else:
    audio_path = wav_files[0]

print("\nSelected:", audio_path.name)

# Distress phrases in English and Hindi
keywords = [
    "help",
    "help me",
    "please help",
    "save me",
    "bachao",
    "bachaao",
    "madad",
    "madad karo",
    "मदद",
    "बचाओ",
    "मुझे बचाओ",
    "मदद करो",
    "छोड़ो",
    "मुझे छोड़ो",
    "मत करो",
]

def normalise_text(text):
    """Lowercase text and remove punctuation."""
    return re.sub(r"[^\w\s]", " ", text.lower()).strip()


def find_distress_keywords(text):
    """Return recognised distress phrases found in the text."""
    normalised = normalise_text(text)
    matches = []

    for keyword in keywords:
        phrase = normalise_text(keyword)
        pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"

        if re.search(pattern, normalised):
            matches.append(keyword)

    return matches


recognizer = sr.Recognizer()
chunk_seconds = 10
results = []
alerts = []
chunk_number = 0

try:
    with sr.AudioFile(str(audio_path)) as source:
        print("\nAnalysing speech in 10-second segments...")

        while True:
            audio_chunk = recognizer.record(
                source,
                duration=chunk_seconds
            )

            # End of audio
            if not audio_chunk.get_raw_data():
                break

            start_time = chunk_number * chunk_seconds
            end_time = start_time + chunk_seconds

            print(
                f"\nChecking {start_time}s to {end_time}s..."
            )

            # Try English (India) and Hindi recognition
            for language in ["en-IN", "hi-IN"]:
                try:
                    transcript = recognizer.recognize_google(
                        audio_chunk,
                        language=language
                    )

                    print(f"Transcript [{language}]: {transcript}")

                    matches = find_distress_keywords(transcript)

                    results.append({
                        "start_seconds": start_time,
                        "language": language,
                        "transcript": transcript,
                        "matched_phrases": ", ".join(matches),
                    })

                    if matches:
                        print("POTENTIAL DISTRESS PHRASE DETECTED!")

                        alerts.append({
                            "start_seconds": start_time,
                            "end_seconds": end_time,
                            "language": language,
                            "transcript": transcript,
                            "matched_phrases": ", ".join(matches),
                            "review_status": "Needs human review",
                        })

                except sr.UnknownValueError:
                    print(
                        f"No clear speech recognised [{language}]."
                    )

                except sr.RequestError as error:
                    raise RuntimeError(
                        "Speech-recognition service failed. "
                        "Check your internet connection. "
                        f"Details: {error}"
                    ) from error

            chunk_number += 1

except (OSError, ValueError) as error:
    raise SystemExit(
        f"Could not read the WAV file: {error}"
    )

# Save results
transcript_path = output_folder / "speech_transcripts.csv"
alerts_path = output_folder / "distress_alerts.csv"

pd.DataFrame(
    results,
    columns=[
        "start_seconds",
        "language",
        "transcript",
        "matched_phrases",
    ],
).to_csv(transcript_path, index=False)

pd.DataFrame(
    alerts,
    columns=[
        "start_seconds",
        "end_seconds",
        "language",
        "transcript",
        "matched_phrases",
        "review_status",
    ],
).to_csv(alerts_path, index=False)

print("\nAudio analysis complete.")
print("Transcripts saved to:", transcript_path)
print("Potential alerts saved to:", alerts_path)
print("Potential alert segments:", len(alerts))
print("Review alerts before taking action.")
