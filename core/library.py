import json
import os

LIBRARY_FILE = os.path.join(os.path.expanduser("~"), ".pyreaderpdf_library.json")


def load_library() -> list:
    """Retorna lista de dicts: {path, name, thumb}"""
    if not os.path.exists(LIBRARY_FILE):
        return []
    try:
        with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def add_to_library(path: str, thumb_path: str = ""):
    library = load_library()
    if any(b["path"] == path for b in library):
        return  # já existe
    name = path.replace("\\", "/").split("/")[-1]
    library.append({"path": path, "name": name, "thumb": thumb_path})
    _save(library)


def remove_from_library(path: str):
    library = [b for b in load_library() if b["path"] != path]
    _save(library)


def update_thumb(path: str, thumb_path: str):
    library = load_library()
    for book in library:
        if book["path"] == path:
            book["thumb"] = thumb_path
            break
    _save(library)


def is_in_library(path: str) -> bool:
    return any(b["path"] == path for b in load_library())


def _save(library: list):
    try:
        with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
            json.dump(library, f, ensure_ascii=False, indent=2)
    except Exception:
        pass