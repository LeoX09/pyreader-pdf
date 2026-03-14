import fitz  # PyMuPDF
from PIL import Image


class PDFDocument:
    """Responsável por abrir, renderizar e navegar num documento PDF."""

    def __init__(self):
        self._doc = None
        self.page_index = 0
        self.zoom = 1.5

    # ------------------------------------------------------------------ Arquivo

    def open(self, path: str):
        """Abre um arquivo PDF. Lança exceção se falhar."""
        self._doc = fitz.open(path)
        self.page_index = 0

    def close(self):
        if self._doc:
            self._doc.close()
            self._doc = None

    @property
    def is_open(self) -> bool:
        return self._doc is not None

    @property
    def total_pages(self) -> int:
        return len(self._doc) if self._doc else 0

    # ------------------------------------------------------------------ Navegação

    def go_to(self, page: int):
        """Vai para uma página (1-indexado externamente)."""
        index = page - 1
        if 0 <= index < self.total_pages:
            self.page_index = index
            return True
        return False

    def next_page(self) -> bool:
        if self._doc and self.page_index < self.total_pages - 1:
            self.page_index += 1
            return True
        return False

    def prev_page(self) -> bool:
        if self._doc and self.page_index > 0:
            self.page_index -= 1
            return True
        return False

    # ------------------------------------------------------------------ Zoom

    def zoom_in(self):
        self.zoom = min(self.zoom + 0.25, 4.0)

    def zoom_out(self):
        self.zoom = max(self.zoom - 0.25, 0.5)

    def zoom_reset(self):
        self.zoom = 1.5

    # ------------------------------------------------------------------ Renderização

    def render_current_page(self) -> Image.Image:
        """Renderiza a página atual e retorna uma imagem PIL."""
        if not self._doc:
            raise RuntimeError("Nenhum documento aberto.")
        page = self._doc[self.page_index]
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
