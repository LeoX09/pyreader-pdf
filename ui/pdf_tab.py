import fitz
import core.config as config
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QStackedWidget, QPushButton, QSplitter)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut, QGuiApplication

from ui.pdf_view import PDFView
from ui.pdf_continuous_view import PDFContinuousView
from ui.notes_panel import NotesPanel
from ui.thumbnails_panel import SidebarPanel
from ui.highlight_bar import HighlightBar
from core.highlights import save_highlight

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
        self._pending_text        = ""
        self._pending_page        = 0
        self._pending_remove_id   = -1
        self._pending_remove_page = -1
        self._build(path)

    # ------------------------------------------------------------------ Build

    def _build(self, path: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        outer = QHBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        root.addLayout(outer)

        try:
            self._doc = fitz.open(path)

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

            self._splitter = QSplitter(Qt.Orientation.Horizontal)
            self._splitter.setHandleWidth(4)
            self._splitter.setChildrenCollapsible(False)
            self._splitter.setStyleSheet("""
                QSplitter::handle { background: #222; }
                QSplitter::handle:hover { background: #2980b9; }
            """)
            outer.addWidget(self._splitter)

            self._sidebar = SidebarPanel(self._doc, self)
            self._sidebar.topic_requested.connect(lambda i: self.go_to(i + 1))
            self._sidebar.visibility_changed.connect(self._on_sidebar_visibility)
            self._splitter.addWidget(self._sidebar)

            viewer_w = QWidget()
            viewer_layout = QVBoxLayout(viewer_w)
            viewer_layout.setContentsMargins(0, 0, 0, 0)
            viewer_layout.setSpacing(0)
            self._splitter.addWidget(viewer_w)

            self._splitter.setSizes([220, 9999])
            self._splitter.setStretchFactor(0, 0)
            self._splitter.setStretchFactor(1, 1)
            self._sidebar.setMinimumWidth(100)

            self._stack = QStackedWidget()

            self._single = PDFView(self._doc, path, self)
            self._single.page_changed.connect(self.page_changed)
            self._single.zoom_changed.connect(self.zoom_changed)
            self._single.text_signals.text_selected.connect(self._on_text_selected)
            self._single.text_signals.selection_cleared.connect(self._on_selection_cleared)
            self._single.text_signals.highlight_clicked.connect(self._on_highlight_clicked)

            self._continuous = PDFContinuousView(self._doc, path, self)
            self._continuous.page_changed.connect(self.page_changed)
            self._continuous.zoom_changed.connect(self.zoom_changed)
            self._continuous.text_signals.text_selected.connect(self._on_text_selected)
            self._continuous.text_signals.selection_cleared.connect(self._on_selection_cleared)
            self._continuous.text_signals.highlight_clicked.connect(self._on_highlight_clicked)

            self._stack.addWidget(self._single)
            self._stack.addWidget(self._continuous)
            self._stack.setCurrentIndex(
                1 if self._mode == MODE_CONTINUOUS else 0)

            viewer_layout.addWidget(self._stack)

            self._notes = NotesPanel(path, self)
            self._notes.go_to_page_requested.connect(self._go_to_page_from_note)
            self._notes.close_requested.connect(self.toggle_notes)
            self._notes.hide()
            outer.addWidget(self._notes)

            # ---- Highlight bar (overlay flutuante) ----
            self._highlight_bar = HighlightBar(self)
            self._highlight_bar.color_chosen.connect(self._save_highlight)
            self._highlight_bar.copy_requested.connect(self._copy_selection)
            self._highlight_bar.note_requested.connect(self._save_pending_selection)
            self._highlight_bar.dismissed.connect(self._dismiss_highlight_bar)
            self._highlight_bar.remove_requested.connect(self._remove_highlight)
            self._highlight_bar.raise_()

            QShortcut(QKeySequence("Ctrl+Shift+N"), self).activated.connect(
                self._save_pending_selection)
            QShortcut(QKeySequence("Ctrl+Shift+B"), self).activated.connect(
                self.toggle_notes)
            QShortcut(QKeySequence("Ctrl+C"), self).activated.connect(
                self._copy_selection)

        except Exception as e:
            err = QLabel(f"Erro ao abrir:\n{e}")
            err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err.setStyleSheet("color:#e74c3c; font-size:11pt;")
            outer.addWidget(err)

    # ------------------------------------------------------------------ Sidebar

    def _on_sidebar_visibility(self, visible: bool):
        self._sidebar_visible = visible
        self._btn_expand.setVisible(not visible)
        if not visible and self._splitter:
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

    # ------------------------------------------------------------------ Texto / Seleção

    def _on_text_selected(self, text: str, page_index: int):
        self._pending_text = text
        self._pending_page = page_index
        if text and self._highlight_bar:
            self._position_highlight_bar()
            self._highlight_bar.show_selection_mode()

    def _on_highlight_clicked(self, highlight_id: int, page_index: int):
        self._pending_remove_id   = highlight_id
        self._pending_remove_page = page_index
        self._view().clear_selection()
        self._position_highlight_bar()
        self._highlight_bar.show_remove_mode(highlight_id)

    def _remove_highlight(self, highlight_id: int):
        from core.highlights import delete_highlight
        delete_highlight(self.path, highlight_id)
        if self._pending_remove_page >= 0:
            self._view().refresh_highlights(self._pending_remove_page)
        self._pending_remove_id   = -1
        self._pending_remove_page = -1
        self._highlight_bar.hide()

    def _on_selection_cleared(self):
        self._pending_text = ""
        if self._highlight_bar:
            self._highlight_bar.hide()

    def _bar_target_rect(self):
        """
        Retorna QRect (em coords do PDFTab) da seleção ou highlight atual.
        Usado para posicionar a barra flutuante perto do alvo.
        """
        view = self._view()
        if self._pending_remove_id >= 0:
            vp_rect = view.get_highlight_viewport_rect(
                self._pending_remove_id, self._pending_remove_page)
        else:
            vp_rect = view.get_selection_viewport_rect()

        if vp_rect is None:
            return None

        vp = view.viewport()
        from PySide6.QtCore import QRect
        return QRect(
            self.mapFromGlobal(vp.mapToGlobal(vp_rect.topLeft())),
            self.mapFromGlobal(vp.mapToGlobal(vp_rect.bottomRight()))
        ).normalized()

    def _position_highlight_bar(self):
        bar = self._highlight_bar
        bar.adjustSize()

        target = self._bar_target_rect()
        if target and target.isValid():
            # Centraliza horizontalmente sobre a seleção, 6px acima
            bx = target.center().x() - bar.width() // 2
            by = target.top() - bar.height() - 6
            # Mantém dentro dos limites do tab
            bx = max(4, min(bx, self.width()  - bar.width()  - 4))
            by = max(4, by)
            # Se sair pelo topo, exibe abaixo
            if by < 4:
                by = target.bottom() + 6
            bar.move(bx, by)
        else:
            bar.move((self.width() - bar.width()) // 2, 8)

    def _copy_selection(self):
        if self._pending_text:
            QGuiApplication.clipboard().setText(self._pending_text)
            self._dismiss_highlight_bar()

    def _dismiss_highlight_bar(self):
        self._highlight_bar.hide()
        self._pending_text = ""
        self._view().clear_selection()

    # ------------------------------------------------------------------ Marca texto

    def _save_highlight(self, color: str):
        view = self._view()
        selections = view.get_selection_info()   # {page_index: [[x,y,w,h],...]}
        for page_index, doc_rects in selections.items():
            if doc_rects:
                save_highlight(self.path, page_index, doc_rects, color)
                view.refresh_highlights(page_index)
        view.clear_selection()
        self._highlight_bar.hide()
        self._pending_text = ""

    # ------------------------------------------------------------------ Notas

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

    # ------------------------------------------------------------------ Modo de visualização

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._highlight_bar and self._highlight_bar.isVisible():
            self._position_highlight_bar()
            self._highlight_bar.raise_()

    def closeEvent(self, event):
        if self._doc:
            self._doc.close()
        super().closeEvent(event)
