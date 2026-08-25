from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


MAX_HISTORY = 3


def history_path() -> Path:
    root = Path(os.getenv("APPDATA", Path.home())) / "Speako"
    root.mkdir(parents=True, exist_ok=True)
    return root / "history.json"


def save_recording(record: dict[str, Any]) -> None:
    records = [record] + load_recent_recordings()[: MAX_HISTORY - 1]
    history_path().write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def load_recent_recordings() -> list[dict[str, Any]]:
    path = history_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []
