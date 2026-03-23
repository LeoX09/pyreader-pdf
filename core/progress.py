"""
core/progress.py
Salva e restaura a última página lida de cada PDF.

Formato do arquivo (~/.pyreaderpdf/progress.json):
{
    "/caminho/completo/livro.pdf": 42,
    ...
}
"""

import json
from pathlib import Path

_PROGRESS_FILE = Path.home() / ".pyreaderpdf" / "progress.json"


def _load() -> dict:
    try:
        return json.loads(_PROGRESS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict):
    _PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PROGRESS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def save_progress(path: str, page: int):
    """Salva a última página lida de um PDF."""
    data = _load()
    data[path] = page
    _save(data)


def get_progress(path: str) -> int:
    """Retorna a última página salva. Retorna 0 se não houver registro."""
    return _load().get(path, 0)