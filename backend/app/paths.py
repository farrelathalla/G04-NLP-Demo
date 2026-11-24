import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ.get("G04_ARTIFACTS", ROOT / "artifacts"))
TASK1_DIR = ARTIFACTS / "task1"
TASK2_DIR = ARTIFACTS / "task2"
TASK3_DIR = ARTIFACTS / "task3"
DEMO_DIR = ROOT / "demo"
# Optional folder with the full corpus (doc_*.txt) to verify uploads outside the demo set.
CORPUS_DIR = Path(os.environ["G04_CORPUS"]) if os.environ.get("G04_CORPUS") else None
