"""Convenience launcher for AI SafetyGuard backend server."""

import sys
from pathlib import Path

# Add src directory to sys.path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting AI SafetyGuard API server on http://{host}:{port} ...")
    uvicorn.run("safetyguard.api.app:app", host=host, port=port, reload=False)

