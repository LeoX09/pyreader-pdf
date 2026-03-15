import fitz
import core.config as config
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QStackedWidget
from PySide6.QtCore import Signal, Qt

from ui.pdf_view import PDFView
from ui.pdf_continuous_view import PDFContinuousView

MODE_SINGLE     = "single"
MODE_CONTINUOUS = "continuous"


class PDFTab(QWidget):
    """Aba de PDF — alterna entre modo página única e modo contínuo."""

    page_changed = Signal(int, int)
    zoom_changed = Signal(float)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path      = path
        self.filename  = path.replace("\\", "/").split("/")[-1]
        self._doc      = None
        self._mode     = config.get('view_mode') or MODE_CONTINUOUS
        self._single   = None
        self._continuous = None
        self._stack    = None
        self._build(path)

    def _build(self, path: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        try:
            self._doc  = fitz.open(path)

            self._stack = QStackedWidget(self)

            self._single = PDFView(self._doc, self)
            self._single.page_changed.connect(self.page_changed)
            self._single.zoom_changed.connect(self.zoom_changed)

            self._continuous = PDFContinuousView(self._doc, self)
            self._continuous.page_changed.connect(self.page_changed)
            self._continuous.zoom_changed.connect(self.zoom_changed)

            self._stack.addWidget(self._single)      # index 0
            self._stack.addWidget(self._continuous)  # index 1

            # Aplica o modo inicial da config
            if self._mode == MODE_CONTINUOUS:
                self._stack.setCurrentIndex(1)
            else:
                self._stack.setCurrentIndex(0)

            layout.addWidget(self._stack)

        except Exception as e:
            err = QLabel(f"Erro ao abrir o arquivo:\n{e}")
            err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err.setStyleSheet("color:#e74c3c; font-size:11pt;")
            layout.addWidget(err)

    # ------------------------------------------------------------------ Modo

    def toggle_view_mode(self) -> str:
        if self._mode == MODE_SINGLE:
            self._mode = MODE_CONTINUOUS
            # Sincroniza página
            self._continuous.go_to_page(self._single.current_page - 1)
            self._stack.setCurrentIndex(1)
        else:
            self._mode = MODE_SINGLE
            self._single.go_to(self._continuous.current_page - 1)
            self._stack.setCurrentIndex(0)
        return self._mode

    @property
    def view_mode(self) -> str:
        return self._mode

    # ------------------------------------------------------------------ Navegação

    def _view(self):
        return self._continuous if self._mode == MODE_CONTINUOUS else self._single

    def next_page(self):
        v = self._view()
        if v: v.next_page()

    def prev_page(self):
        v = self._view()
        if v: v.prev_page()

    def go_to(self, page: int) -> bool:
        v = self._view()
        if not v:
            return False
        if self._mode == MODE_CONTINUOUS:
            v.go_to_page(page - 1)
        else:
            v.go_to(page - 1)
        return True

    def zoom_in(self):    self._view().zoom_in()
    def zoom_out(self):   self._view().zoom_out()
    def zoom_reset(self): self._view().zoom_reset()

    @property
    def current_page(self) -> int:
        return self._view().current_page if self._view() else 1

    @property
    def total_pages(self) -> int:
        return self._view().total_pages if self._view() else 0

    @property
    def zoom(self) -> float:
        return self._view().zoom if self._view() else 1.5

    def closeEvent(self, event):
        if self._doc:
            self._doc.close()
        super().closeEvent(event)