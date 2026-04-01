import json
import os

LIBRARY_FILE = os.path.join(os.path.expanduser("~"), ".pyreaderpdf_library.json")


def _normalize(entry) -> dict:
    """Normaliza entradas antigas (string ou dict incompleto) para o formato atual."""
    if isinstance(entry, str):
        path = entry
        return {"path": path, "name": path.replace("\\", "/").split("/")[-1], "thumb": ""}
    if isinstance(entry, dict):
        entry.setdefault("name", entry.get("path", "").replace("\\", "/").split("/")[-1])
        entry.setdefault("thumb", "")
        return entry
    return None


def load_library() -> list:
    if not os.path.exists(LIBRARY_FILE):
        return []
    try:
        with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        normalized = [_normalize(e) for e in data]
        return [e for e in normalized if e is not None]
    except Exception:
        return []


def _save(library: list):
    try:
        with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
            json.dump(library, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_to_library(path: str, thumb_path: str = ""):
    library = load_library()
    if any(b["path"] == path for b in library):
        return
    name = path.replace("\\", "/").split("/")[-1]
    library.append({"path": path, "name": name, "thumb": thumb_path})
    _save(library)


def remove_from_library(path: str):
    _save([b for b in load_library() if b["path"] != path])


def update_thumb(path: str, thumb_path: str):
    library = load_library()
    for book in library:
        if book["path"] == path:
            book["thumb"] = thumb_path
            break
    _save(library)


def is_in_library(path: str) -> bool:
    return any(b["path"] == path for b in load_library())


def reorder_library(paths: list):
    library = load_library()
    order   = {p: i for i, p in enumerate(paths)}
    library.sort(key=lambda b: order.get(b["path"], 9999))
    _save(library)