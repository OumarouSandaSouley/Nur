"""
Lance le serveur API :
    python run_server.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
import uvicorn

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

load_dotenv(ROOT / ".env")

if __name__ == "__main__":
    # reload=False : plus stable sur Windows (les jobs en mémoire ne sont pas tués)
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
