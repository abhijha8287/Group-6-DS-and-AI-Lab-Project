"""Small shared helpers: repository paths, time handling, JSON I/O and .env loading.

Standard library only, so the pipeline runs on any Python 3.9+ without extra packages.
"""

from __future__ import annotations

import copy
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = REPO_ROOT / "milestones" / "M2_dataset"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
RUNS_DIR = REPO_ROOT / "experiments" / "runs"

# Every business in the sandbox operates in India; all clock rules use this zone.
BUSINESS_TZ = ZoneInfo("Asia/Kolkata")

# Pilot folder for each business key used across the project.
PILOT_DIRS = {
    "solar": DATASET_DIR / "solar_pilot",
    "dental": DATASET_DIR / "dental_pilot",
    "furniture": DATASET_DIR / "furniture_pilot",
}


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def deep_copy(data):
    return copy.deepcopy(data)


def parse_time(value: str) -> datetime:
    """Parse an ISO timestamp. Naive times are read as business local time."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BUSINESS_TZ)
    return dt.astimezone(BUSINESS_TZ)


def iso(dt: datetime) -> str:
    return dt.astimezone(BUSINESS_TZ).isoformat()


def load_env(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from .env into os.environ (existing values win).

    A tiny replacement for python-dotenv so that secrets never need to be
    passed on the command line.
    """
    path = Path(path) if path else REPO_ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)
