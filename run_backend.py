"""Convenience launcher for AI SafetyGuard backend server."""

import sys
from pathlib import Path

# Add src directory to sys.path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

if __name__ == "__main__":
    import uvicorn
    print("Starting AI SafetyGuard API server on http://127.0.0.1:8000 ...")
    uvicorn.run("safetyguard.api.app:app", host="127.0.0.1", port=8000, reload=False)
