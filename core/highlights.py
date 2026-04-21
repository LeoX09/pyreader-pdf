import json
import os
import hashlib

HIGHLIGHTS_DIR = os.path.join(os.path.expanduser("~"), ".pyreaderpdf_highlights")


def _path(pdf_path: str) -> str:
    os.makedirs(HIGHLIGHTS_DIR, exist_ok=True)
    key = hashlib.md5(pdf_path.encode()).hexdigest()
    return os.path.join(HIGHLIGHTS_DIR, f"{key}.json")


def load_highlights(pdf_path: str) -> list:
    """Returns list of {id, page, rects: [[x,y,w,h],...], color} in document coords."""
    p = _path(pdf_path)
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(pdf_path: str, highlights: list):
    try:
        with open(_path(pdf_path), "w", encoding="utf-8") as f:
            json.dump(highlights, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def save_highlight(pdf_path: str, page: int, rects: list, color: str = "#f6c90e") -> dict:
    """rects: list of [x, y, w, h] in document coordinates."""
    highlights = load_highlights(pdf_path)
    entry = {"id": len(highlights), "page": page, "rects": rects, "color": color}
    highlights.append(entry)
    _save(pdf_path, highlights)
    return entry


def delete_highlight(pdf_path: str, highlight_id: int):
    _save(pdf_path, [h for h in load_highlights(pdf_path) if h["id"] != highlight_id])


def get_page_highlights(pdf_path: str, page: int) -> list:
    return [h for h in load_highlights(pdf_path) if h["page"] == page]
