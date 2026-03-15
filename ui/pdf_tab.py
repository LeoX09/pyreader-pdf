import fitz
import core.config as config
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut

from ui.pdf_view import PDFView
from ui.pdf_continuous_view import PDFContinuousView
from ui.notes_panel import NotesPanel

MODE_SINGLE     = "single"
MODE_CONTINUOUS = "continuous"


class PDFTab(QWidget):
    """Aba de PDF com visualizador + painel de notas lateral."""

    page_changed = Signal(int, int)
    zoom_changed = Signal(float)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path      = path
        self.filename  = path.replace("\\", "/").split("/")[-1]
        self._doc      = None
        self._mode     = config.get("view_mode") or MODE_CONTINUOUS
        self._single     = None
        self._continuous = None
        self._stack      = None
        self._notes      = None
        self._notes_visible = False
        self._build(path)

    # ------------------------------------------------------------------ Build

    def _build(self, path: str):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Área do visualizador
        viewer_w = QWidget()
        viewer_layout = QVBoxLayout(viewer_w)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.setSpacing(0)
        outer.addWidget(viewer_w, stretch=1)

        try:
            self._doc = fitz.open(path)

            self._stack = QStackedWidget()

            self._single = PDFView(self._doc, self)
            self._single.page_changed.connect(self.page_changed)
            self._single.zoom_changed.connect(self.zoom_changed)
            self._single.text_signals.text_selected.connect(self._on_text_selected)

            self._continuous = PDFContinuousView(self._doc, self)
            self._continuous.page_changed.connect(self.page_changed)
            self._continuous.zoom_changed.connect(self.zoom_changed)
            self._continuous.text_signals.text_selected.connect(self._on_text_selected)

            self._stack.addWidget(self._single)      # 0
            self._stack.addWidget(self._continuous)  # 1

            if self._mode == MODE_CONTINUOUS:
                self._stack.setCurrentIndex(1)
            else:
                self._stack.setCurrentIndex(0)

            viewer_layout.addWidget(self._stack)

            # Notas panel
            self._notes = NotesPanel(path, self)
            self._notes.go_to_page_requested.connect(self._go_to_page_from_note)
            self._notes.hide()
            outer.addWidget(self._notes)

            # Atalho Ctrl+Shift+N — cria nota da seleção
            sc = QShortcut(QKeySequence("Ctrl+Shift+N"), self)
            sc.activated.connect(self._save_pending_selection)

            # Atalho Ctrl+Shift+B — abre/fecha painel
            sc2 = QShortcut(QKeySequence("Ctrl+Shift+B"), self)
            sc2.activated.connect(self.toggle_notes)

        except Exception as e:
            err = QLabel(f"Erro ao abrir:\n{e}")
            err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err.setStyleSheet("color:#e74c3c; font-size:11pt;")
            viewer_layout.addWidget(err)

        self._pending_text  = ""
        self._pending_page  = 0

    # ------------------------------------------------------------------ Notas

    def _on_text_selected(self, text: str, page_index: int):
        """Guarda a seleção pendente — Ctrl+Shift+N cria a nota."""
        self._pending_text = text
        self._pending_page = page_index

    def _save_pending_selection(self):
        if not self._pending_text or not self._notes:
            return
        if not self._notes_visible:
            self.toggle_notes()
        self._notes.add_citation(self._pending_text, self._pending_page)
        self._pending_text = ""

    def toggle_notes(self):
        if not self._notes:
            return
        self._notes_visible = not self._notes_visible
        if self._notes_visible:
            self._notes.show()
        else:
            self._notes.hide()

    def _go_to_page_from_note(self, page_index: int):
        self.go_to(page_index + 1)

    # ------------------------------------------------------------------ Modo

    def toggle_view_mode(self) -> str:
        if self._mode == MODE_SINGLE:
            self._mode = MODE_CONTINUOUS
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
        if not v: return False
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