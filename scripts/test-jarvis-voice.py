"""Run LiveKit against staged source using the user's existing credentials in memory."""
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

workspace = Path(__file__).resolve().parents[1]
original = Path(r"C:\J.A.R.V.I.S\jarvis")
load_dotenv(original / ".env.local")
os.environ["UV_PROJECT_ENVIRONMENT"] = str(original / ".venv")
os.environ["UV_NO_SYNC"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
stage = workspace / ".local/jarvis-work"
args = sys.argv[1:]
if args == ["simulate"]:
    args = ["agent", "simulate", "text", "--scenarios", "scenarios.yaml", "--concurrency", "2", "--yes"]
elif args == ["start"]:
    args = ["agent", "debugger", "start", "--audio", "--port", "8786", "--idle-timeout", "5m"]
result = subprocess.run(["lk", *args], cwd=stage)
raise SystemExit(result.returncode)
