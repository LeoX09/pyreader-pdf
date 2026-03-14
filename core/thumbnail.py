import os
import hashlib
import fitz
from PIL import Image

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".pyreaderpdf_thumbs")
THUMB_W = 160
THUMB_H = 220


def _ensure_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _thumb_path(pdf_path: str) -> str:
    key = hashlib.md5(pdf_path.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{key}.png")


def get_thumbnail(pdf_path: str) -> str | None:
    """
    Retorna o caminho da miniatura PNG gerada da capa do PDF.
    Usa cache: só renderiza uma vez.
    """
    _ensure_cache()
    out = _thumb_path(pdf_path)

    if os.path.exists(out):
        return out

    if not os.path.exists(pdf_path):
        return None

    try:
        doc = fitz.open(pdf_path)
        page = doc[0]

        # Calcula zoom para caber em THUMB_W x THUMB_H mantendo proporção
        rect = page.rect
        zoom_x = THUMB_W / rect.width
        zoom_y = THUMB_H / rect.height
        zoom = min(zoom_x, zoom_y) * 2  # 2x para qualidade
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        doc.close()

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Redimensiona para tamanho exato com padding branco
        img.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)
        canvas = Image.new("RGB", (THUMB_W, THUMB_H), (40, 40, 40))
        offset_x = (THUMB_W - img.width) // 2
        offset_y = (THUMB_H - img.height) // 2
        canvas.paste(img, (offset_x, offset_y))
        canvas.save(out, "PNG")
        return out
    except Exception:
        return None


def invalidate(pdf_path: str):
    """Remove a miniatura do cache (ex: após troca de capa)."""
    path = _thumb_path(pdf_path)
    if os.path.exists(path):
        os.remove(path)