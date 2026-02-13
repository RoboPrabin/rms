import json
from pathlib import Path


def load_lottie_file(filepath: str):
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Lottie file not found: {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
