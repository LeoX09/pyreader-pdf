from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QFileDialog, QTabBar
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QKeySequence, QShortcut, QPainter, QColor
from PySide6.QtWidgets import QApplication

from core.history import add_recent
from core.library import add_to_library
from ui.toolbar import Toolbar
from ui.home import HomeScreen
from ui.statusbar import Statusbar
from ui.pdf_tab import PDFTab, MODE_SINGLE, MODE_CONTINUOUS
from ui.split_view import SplitView
from ui.settings import SettingsDialog
import core.config as config


# ------------------------------------------------------------------ Drop overlay

class DropOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._side = "none"

    def set_side(self, side: str):
        self._side = side
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        lc = QColor(26, 107, 60, 180 if self._side == "left"  else 70)
        rc = QColor(26,  79, 107, 180 if self._side == "right" else 70)
        p.fillRect(0, 0, w // 2, h, lc)
        p.fillRect(w // 2, 0, w // 2, h, rc)
        from PySide6.QtGui import QFont
        from PySide6.QtCore import QRect
        f = QFont(); f.setPointSize(13); f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 200))
        p.drawText(QRect(0, 0, w // 2, h), Qt.AlignmentFlag.AlignCenter, "◧  Esquerda")
        p.drawText(QRect(w // 2, 0, w // 2, h), Qt.AlignmentFlag.AlignCenter, "◨  Direita")
        p.end()


# ------------------------------------------------------------------ TabBar com drag

class DraggableTabBar(QTabBar):
    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self._app      = app_ref
        self._drag_idx = -1
        self._start    = QPoint()
        self._dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_idx = self.tabAt(event.pos())
            self._start    = event.pos()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_idx > 0 and event.buttons() & Qt.MouseButton.LeftButton:
            dy = event.pos().y() - self._start.y()
            dl = (event.pos() - self._start).manhattanLength()
            if not self._dragging and dl > 15 and dy > 10:
                self._dragging = True
            if self._dragging:
                gp   = event.globalPosition().toPoint()
                side = self._app.global_pos_to_side(gp)
                self._app.show_drop_overlay(side)
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging and self._drag_idx > 0:
            self._dragging = False
            gp   = event.globalPosition().toPoint()
            side = self._app.global_pos_to_side(gp)
            self._app.hide_drop_overlay()
            self._app.create_split_from_drag(self._drag_idx, side)
            self._drag_idx = -1
            return
        self._dragging = False
        self._drag_idx = -1
        super().mouseReleaseEvent(event)


# ------------------------------------------------------------------ App principal

class App(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyReaderPDF")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("QMainWindow { background:#1e1e1e; }")

        self._tab_paths    = {}   # tab index -> path
        self._split_widget = None
        self._split_tabs   = []
        self._drop_overlay = None


        self._build_ui()
        self._bind_shortcuts()

    # ------------------------------------------------------------------ Build

    def _build_ui(self):
        self._toolbar = Toolbar(self)
        self.addToolBar(self._toolbar)
        self._connect_toolbar()

        self._statusbar = Statusbar(self)
        self.setStatusBar(self._statusbar)

        self._tabs = QTabWidget()
        self._tabs.setTabBar(DraggableTabBar(self, self._tabs))
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True)
        self._tabs.setStyleSheet(self._tab_style())
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tabs)

        self._home = HomeScreen()
        self._home.open_requested.connect(self.open_path)
        self._tabs.addTab(self._home, "⌂  Início")
        self._tabs.tabBar().setTabButton(
            0, QTabBar.ButtonPosition.RightSide, None)

        self._toolbar.set_pdf_enabled(False)

    def _connect_toolbar(self):
        self._toolbar.open_requested.connect(self.open_file)
        self._toolbar.prev_requested.connect(self.prev_page)
        self._toolbar.next_requested.connect(self.next_page)
        self._toolbar.go_to_requested.connect(self.go_to_page)
        self._toolbar.zoom_in_requested.connect(self.zoom_in)
        self._toolbar.zoom_out_requested.connect(self.zoom_out)
        self._toolbar.zoom_reset_requested.connect(self.zoom_reset)
        self._toolbar.add_library_requested.connect(self.add_active_to_library)
        self._toolbar.settings_requested.connect(self.open_settings)

    def _bind_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"),     self).activated.connect(self.open_file)
        QShortcut(QKeySequence("Ctrl+D"),     self).activated.connect(self.duplicate_tab)
        QShortcut(QKeySequence("Ctrl+W"),     self).activated.connect(self.close_split_or_tab)
        QShortcut(QKeySequence("Escape"),     self).activated.connect(self.close_split)
        QShortcut(QKeySequence("Ctrl+Right"), self).activated.connect(
            lambda: self._split_active_tab("right"))
        QShortcut(QKeySequence("Ctrl+Left"),  self).activated.connect(
            lambda: self._split_active_tab("left"))

    # ------------------------------------------------------------------ Abrir

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar PDF", "", "Arquivos PDF (*.pdf *.PDF)")
        if path:
            self.open_path(path)

    def open_path(self, path: str):
        for i, p in self._tab_paths.items():
            if p == path:
                self._tabs.setCurrentIndex(i)
                return
        add_recent(path)
        add_to_library(path)
        self._home.refresh()
        self._open_tab(path)

    def _open_tab(self, path: str, suffix: str = "") -> PDFTab:
        filename = path.replace("\\", "/").split("/")[-1]
        short    = filename if len(filename) <= 24 else filename[:21] + "..."
        if suffix:
            short += f" {suffix}"

        tab = PDFTab(path, self)
        tab.page_changed.connect(self._on_page_changed)
        tab.zoom_changed.connect(self._on_zoom_changed)

        idx = self._tabs.addTab(tab, short)
        self._tab_paths[idx] = path
        self._tabs.setCurrentIndex(idx)
        return tab

    # ------------------------------------------------------------------ Duplicar

    def duplicate_tab(self):
        tab = self._active_tab()
        if not tab:
            return
        self._open_tab(tab.path, suffix="(2)")
        self._statusbar.set_message(
            "Aba duplicada — Ctrl+→ ou Ctrl+← para criar Split View")

    # ------------------------------------------------------------------ Split via atalho

    def _split_active_tab(self, side: str):
        """Ctrl+→ ou Ctrl+← — cria split com a aba atual e a adjacente."""
        if self._split_widget:
            self.close_split()
            return

        active_idx = self._tabs.currentIndex()
        if not isinstance(self._tabs.widget(active_idx), PDFTab):
            return

        # Busca outra aba PDF para colocar no outro lado
        other_idx = None
        for i in range(self._tabs.count()):
            if i != active_idx and isinstance(self._tabs.widget(i), PDFTab):
                other_idx = i
                break

        if other_idx is None:
            # Não há outra aba — duplica automaticamente
            active_tab = self._tabs.widget(active_idx)
            path       = active_tab.path
            filename   = active_tab.filename
            if side == "right":
                self._enter_split(path, path, filename, filename + " (2)")
            else:
                self._enter_split(path, path, filename + " (2)", filename)
            return

        other_tab = self._tabs.widget(other_idx)
        if side == "right":
            self._enter_split(
                self._tabs.widget(active_idx).path, other_tab.path,
                self._tabs.widget(active_idx).filename, other_tab.filename)
        else:
            self._enter_split(
                other_tab.path, self._tabs.widget(active_idx).path,
                other_tab.filename, self._tabs.widget(active_idx).filename)

    # ------------------------------------------------------------------ Split via drag

    def global_pos_to_side(self, global_pos: QPoint) -> str:
        w = self._tabs.currentWidget()
        if not w:
            return "right"
        local = w.mapFromGlobal(global_pos)
        return "left" if local.x() < w.width() // 2 else "right"

    def show_drop_overlay(self, side: str):
        content = self._tabs.currentWidget()
        if not content:
            return
        if self._drop_overlay is None:
            self._drop_overlay = DropOverlay(content)
            self._drop_overlay.resize(content.size())
            self._drop_overlay.show()
        self._drop_overlay.set_side(side)

    def hide_drop_overlay(self):
        if self._drop_overlay:
            self._drop_overlay.hide()
            self._drop_overlay.deleteLater()
            self._drop_overlay = None

    def create_split_from_drag(self, dragged_idx: int, side: str):
        active_idx = self._tabs.currentIndex()
        dragged_w  = self._tabs.widget(dragged_idx)
        active_w   = self._tabs.widget(active_idx)

        if not isinstance(dragged_w, PDFTab) or not isinstance(active_w, PDFTab):
            return
        if dragged_idx == active_idx:
            # Mesmo tab — abre o mesmo arquivo nos dois lados
            self._enter_split(
                dragged_w.path, dragged_w.path,
                dragged_w.filename, dragged_w.filename + " (2)")
            return

        if side == "left":
            self._enter_split(
                dragged_w.path, active_w.path,
                dragged_w.filename, active_w.filename)
        else:
            self._enter_split(
                active_w.path, dragged_w.path,
                active_w.filename, dragged_w.filename)

    def _enter_split(self, left_path: str, right_path: str,
                     left_name: str, right_name: str):
        if self._split_widget:
            self.close_split()

        left_tab  = PDFTab(left_path,  self)
        right_tab = PDFTab(right_path, self)

        self._split_tabs = [left_tab, right_tab]

        split = SplitView(left_tab, right_tab, left_name, right_name, self)
        split.closed.connect(self.close_split)
        self._split_widget = split

        self._tabs.hide()
        self.takeCentralWidget()
        self.setCentralWidget(split)

        self._toolbar.set_pdf_enabled(False)
        self.setWindowTitle("PyReaderPDF — Split View")
        self._statusbar.set_message(
            "Split View ativo  |  Esc ou Ctrl+W para fechar  |  "
            "Ctrl+→/← para trocar  |  Arraste o divisor para redimensionar")

    def close_split(self):
        if not self._split_widget:
            return
        for tab in self._split_tabs:
            tab.deleteLater()
        self._split_tabs   = []
        self._split_widget.deleteLater()
        self._split_widget = None

        self.takeCentralWidget()
        self.setCentralWidget(self._tabs)
        self._tabs.show()
        self._on_tab_changed(self._tabs.currentIndex())

    def close_split_or_tab(self):
        if self._split_widget:
            self.close_split()
        else:
            idx = self._tabs.currentIndex()
            if idx > 0:
                self._close_tab(idx)

    # ------------------------------------------------------------------ Abas

    def _close_tab(self, index: int):
        if index == 0:
            return
        w = self._tabs.widget(index)
        self._tabs.removeTab(index)
        self._rebuild_tab_paths()
        if w:
            w.deleteLater()

    def _rebuild_tab_paths(self):
        self._tab_paths = {}
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if isinstance(w, PDFTab):
                self._tab_paths[i] = w.path

    def _on_tab_changed(self, index: int):
        w = self._tabs.widget(index)
        if isinstance(w, PDFTab):
            self.setWindowTitle(f"PyReaderPDF — {w.filename}")
            self._toolbar.set_pdf_enabled(True)
            self._toolbar.update_page(w.current_page, w.total_pages)
            self._toolbar.update_zoom(w.zoom)
            self._statusbar.update(w.current_page, w.total_pages, w.zoom)
        else:
            self.setWindowTitle("PyReaderPDF")
            self._toolbar.set_pdf_enabled(False)
            self._statusbar.set_message("Início")

    def _active_tab(self) -> PDFTab | None:
        w = self._tabs.currentWidget()
        return w if isinstance(w, PDFTab) else None

    # ------------------------------------------------------------------ Callbacks toolbar

    def _on_page_changed(self, current: int, total: int):
        if isinstance(self._tabs.currentWidget(), PDFTab):
            self._toolbar.update_page(current, total)
            tab = self._active_tab()
            if tab:
                self._statusbar.update(current, total, tab.zoom)

    def _on_zoom_changed(self, zoom: float):
        tab = self._active_tab()
        if tab:
            self._statusbar.update(tab.current_page, tab.total_pages, zoom)
            self._toolbar.update_zoom(zoom)

    def prev_page(self):
        tab = self._active_tab()
        if tab: tab.prev_page()

    def next_page(self):
        tab = self._active_tab()
        if tab: tab.next_page()

    def go_to_page(self, page: int):
        tab = self._active_tab()
        if tab and not tab.go_to(page):
            self._statusbar.set_message(f"Página inválida. Total: {tab.total_pages}")

    def zoom_in(self):
        tab = self._active_tab()
        if tab: tab.zoom_in()

    def zoom_out(self):
        tab = self._active_tab()
        if tab: tab.zoom_out()

    def zoom_reset(self):
        tab = self._active_tab()
        if tab: tab.zoom_reset()

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.settings_changed.connect(self._apply_settings)
        dlg.exec()

    def _apply_settings(self):
        """Aplica novas configurações em todas as abas abertas."""
        mode = config.get("view_mode")
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if isinstance(w, PDFTab) and w.view_mode != mode:
                w.toggle_view_mode()
        for tab in self._split_tabs:
            if tab.view_mode != mode:
                tab.toggle_view_mode()
        self._statusbar.set_message("Configurações salvas")

    def add_active_to_library(self):
        tab = self._active_tab()
        if tab:
            add_to_library(tab.path)
            self._home.refresh()
            self._statusbar.set_message(f"'{tab.filename}' adicionado à biblioteca")

    # ------------------------------------------------------------------ Estilo

    def _tab_style(self):
        return """
        QTabWidget::pane { border:none; background:#1e1e1e; }
        QTabBar           { background:#141414; }
        QTabBar::tab {
            background:#2a2a2a; color:#999;
            padding:7px 16px; margin-right:1px;
            font-size:9pt; min-width:80px;
        }
        QTabBar::tab:selected {
            background:#1e1e1e; color:white;
            border-top:2px solid #2980b9;
        }
        QTabBar::tab:hover:!selected { background:#333; color:#ccc; }
        """