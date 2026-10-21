import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WINDOWS = sys.platform == "win32"


def python_for(project):
    if WINDOWS:
        return project / ".venv" / "Scripts" / "python.exe"

    return project / ".venv" / "bin" / "python"


processes = []

# Backend
backend = ROOT / "backend"
backend_python = python_for(backend)

if backend.exists() and backend_python.exists():
    print("Starting backend...")

    processes.append(
        subprocess.Popen(
            [
                str(backend_python),
                "-m",
                "flask",
                "--app",
                "app",
                "run",
                "--debug",
            ],
            cwd=backend,
        )
    )

# Frontend
frontend = ROOT / "frontend"
frontend_python = python_for(frontend)

if frontend.exists() and frontend_python.exists():
    print("Starting frontend...")

    processes.append(
        subprocess.Popen(
            [
                str(frontend_python),
                "-m",
                "streamlit",
                "run",
                "app.py",
            ],
            cwd=frontend,
        )
    )

if not processes:
    print("No runnable applications found. Run 'make build' first.")
    sys.exit(1)

try:
    for process in processes:
        process.wait()
except KeyboardInterrupt:
    pass
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        process.wait()