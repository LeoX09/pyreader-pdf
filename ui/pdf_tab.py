import fitz
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Signal, Qt

from ui.pdf_view import PDFView


class PDFTab(QWidget):
    """
    Conteúdo de uma aba de PDF.
    Gerencia o documento e expõe sinais para o App.
    """

    page_changed = Signal(int, int)   # current, total
    zoom_changed = Signal(float)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path     = path
        self.filename = path.replace("\\", "/").split("/")[-1]
        self._doc     = None
        self._view    = None

        self._build(path)

    # ------------------------------------------------------------------ Build

    def _build(self, path: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        try:
            self._doc  = fitz.open(path)
            self._view = PDFView(self._doc, self)
            self._view.page_changed.connect(self.page_changed)
            self._view.zoom_changed.connect(self.zoom_changed)
            layout.addWidget(self._view)
        except Exception as e:
            err = QLabel(f"Erro ao abrir o arquivo:\n{e}")
            err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err.setStyleSheet("color:#e74c3c; font-size:11pt;")
            layout.addWidget(err)

    # ------------------------------------------------------------------ API

    def next_page(self):
        if self._view: self._view.next_page()

    def prev_page(self):
        if self._view: self._view.prev_page()

    def go_to(self, page: int) -> bool:
        if self._view:
            self._view.go_to(page - 1)
            return True
        return False

    def zoom_in(self):
        if self._view: self._view.zoom_in()

    def zoom_out(self):
        if self._view: self._view.zoom_out()

    def zoom_reset(self):
        if self._view: self._view.zoom_reset()

    @property
    def current_page(self) -> int:
        return self._view.current_page if self._view else 1

    @property
    def total_pages(self) -> int:
        return self._view.total_pages if self._view else 0

    @property
    def zoom(self) -> float:
        return self._view.zoom if self._view else 1.5

    def closeEvent(self, event):
        if self._doc:
            self._doc.close()
        super().closeEvent(event)