import sys
from pathlib import Path

# Add greenhouse_gateway/ to the import path so tests can import subscriber.py
sys.path.insert(0, str(Path(__file__).parent.parent))