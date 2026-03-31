import fitz
import core.config as config
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QStackedWidget, QPushButton, QSplitter)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut

from ui.pdf_view import PDFView
from ui.pdf_continuous_view import PDFContinuousView
from ui.notes_panel import NotesPanel
from ui.thumbnails_panel import SidebarPanel

MODE_SINGLE     = "single"
MODE_CONTINUOUS = "continuous"


class PDFTab(QWidget):
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
        self._sidebar    = None
        self._splitter   = None
        self._notes      = None
        self._notes_visible   = False
        self._sidebar_visible = True
        self._build(path)

    # ------------------------------------------------------------------ Build

    def _build(self, path: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Layout externo: [btn_expand] [splitter]
        outer = QHBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        root.addLayout(outer)

        try:
            self._doc = fitz.open(path)

            # ---- Botão expandir (oculto inicialmente) ----
            self._btn_expand = QPushButton("›")
            self._btn_expand.setFixedWidth(16)
            self._btn_expand.setToolTip("Expandir painel lateral")
            self._btn_expand.setCursor(Qt.CursorShape.PointingHandCursor)
            self._btn_expand.setStyleSheet("""
                QPushButton {
                    background: #1e1e1e; color: #444; border: none;
                    border-right: 1px solid #2a2a2a; font-size: 11pt;
                }
                QPushButton:hover { color: white; background: #2a2a2a; }
            """)
            self._btn_expand.clicked.connect(self._expand_sidebar)
            self._btn_expand.hide()
            outer.addWidget(self._btn_expand)

            # ---- Splitter principal ----
            self._splitter = QSplitter(Qt.Orientation.Horizontal)
            self._splitter.setHandleWidth(4)
            self._splitter.setChildrenCollapsible(False)
            self._splitter.setStyleSheet("""
                QSplitter::handle {
                    background: #222;
                }
                QSplitter::handle:hover {
                    background: #2980b9;
                }
            """)
            outer.addWidget(self._splitter)

            # ---- Sidebar ----
            self._sidebar = SidebarPanel(self._doc, self)
            self._sidebar.topic_requested.connect(lambda i: self.go_to(i + 1))
            self._sidebar.visibility_changed.connect(self._on_sidebar_visibility)
            self._splitter.addWidget(self._sidebar)

            # ---- Visualizador (centro) ----
            viewer_w = QWidget()
            viewer_layout = QVBoxLayout(viewer_w)
            viewer_layout.setContentsMargins(0, 0, 0, 0)
            viewer_layout.setSpacing(0)
            self._splitter.addWidget(viewer_w)

            # Proporcões iniciais: sidebar 170px, resto para o viewer
            self._splitter.setSizes([220, 9999])
            # Sidebar não colapsa abaixo de 100px, viewer abaixo de 300px
            self._splitter.setStretchFactor(0, 0)
            self._splitter.setStretchFactor(1, 1)
            self._sidebar.setMinimumWidth(100)

            self._stack = QStackedWidget()

            self._single = PDFView(self._doc, self)
            self._single.page_changed.connect(self.page_changed)
            self._single.zoom_changed.connect(self.zoom_changed)
            self._single.text_signals.text_selected.connect(self._on_text_selected)

            self._continuous = PDFContinuousView(self._doc, self)
            self._continuous.page_changed.connect(self.page_changed)
            self._continuous.zoom_changed.connect(self.zoom_changed)
            self._continuous.text_signals.text_selected.connect(self._on_text_selected)

            self._stack.addWidget(self._single)
            self._stack.addWidget(self._continuous)
            self._stack.setCurrentIndex(
                1 if self._mode == MODE_CONTINUOUS else 0)

            viewer_layout.addWidget(self._stack)

            # ---- Notas (direita, fora do splitter) ----
            self._notes = NotesPanel(path, self)
            self._notes.go_to_page_requested.connect(self._go_to_page_from_note)
            self._notes.hide()
            outer.addWidget(self._notes)

            QShortcut(QKeySequence("Ctrl+Shift+N"), self).activated.connect(
                self._save_pending_selection)
            QShortcut(QKeySequence("Ctrl+Shift+B"), self).activated.connect(
                self.toggle_notes)

        except Exception as e:
            err = QLabel(f"Erro ao abrir:\n{e}")
            err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err.setStyleSheet("color:#e74c3c; font-size:11pt;")
            outer.addWidget(err)

        self._pending_text = ""
        self._pending_page = 0

    # ------------------------------------------------------------------ Sidebar

    def _on_sidebar_visibility(self, visible: bool):
        self._sidebar_visible = visible
        self._btn_expand.setVisible(not visible)
        if not visible and self._splitter:
            # Guarda tamanho atual antes de esconder
            sizes = self._splitter.sizes()
            self._last_sidebar_size = sizes[0] if sizes[0] > 0 else 170
            self._splitter.setSizes([0, sum(sizes)])

    def _expand_sidebar(self):
        self._sidebar_visible = True
        self._btn_expand.hide()
        self._sidebar.show()
        if self._splitter:
            total = sum(self._splitter.sizes())
            size  = getattr(self, "_last_sidebar_size", 170)
            self._splitter.setSizes([size, total - size])

    # ------------------------------------------------------------------ Notas

    def _on_text_selected(self, text: str, page_index: int):
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
        self._notes.setVisible(self._notes_visible)

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