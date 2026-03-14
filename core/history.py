import json
import os
from datetime import datetime

HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".pyreaderpdf_history.json")
MAX_RECENT = 20


def load_recent() -> list:
    """Retorna lista de dicts: {path, name, last_opened}"""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def add_recent(path: str):
    recent = load_recent()
    recent = [r for r in recent if r["path"] != path]
    name = path.replace("\\", "/").split("/")[-1]
    recent.insert(0, {
        "path": path,
        "name": name,
        "last_opened": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    recent = recent[:MAX_RECENT]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(recent, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def remove_recent(path: str):
    recent = [r for r in load_recent() if r["path"] != path]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(recent, f, ensure_ascii=False, indent=2)