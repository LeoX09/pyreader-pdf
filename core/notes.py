import json
import os
import hashlib
from datetime import datetime

NOTES_DIR = os.path.join(os.path.expanduser("~"), ".pyreaderpdf_notes")


def _notes_path(pdf_path: str) -> str:
    os.makedirs(NOTES_DIR, exist_ok=True)
    key = hashlib.md5(pdf_path.encode()).hexdigest()
    return os.path.join(NOTES_DIR, f"{key}.json")


def load_notes(pdf_path: str) -> list:
    """Retorna lista de notas: {id, page, quote, note, color, created}"""
    path = _notes_path(pdf_path)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_note(pdf_path: str, page: int, quote: str,
              note: str = "", color: str = "#f6c90e") -> dict:
    notes = load_notes(pdf_path)
    entry = {
        "id":      len(notes),
        "page":    page,
        "quote":   quote,
        "note":    note,
        "color":   color,
        "created": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    notes.append(entry)
    with open(_notes_path(pdf_path), "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    return entry


def update_note(pdf_path: str, note_id: int, note_text: str):
    notes = load_notes(pdf_path)
    for n in notes:
        if n["id"] == note_id:
            n["note"] = note_text
            break
    with open(_notes_path(pdf_path), "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


def delete_note(pdf_path: str, note_id: int):
    notes = [n for n in load_notes(pdf_path) if n["id"] != note_id]
    with open(_notes_path(pdf_path), "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)