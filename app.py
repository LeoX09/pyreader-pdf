from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut

from core.history import add_recent
from core.library import add_to_library
from ui.toolbar import Toolbar
from ui.home import HomeScreen
from ui.statusbar import Statusbar


class App(QMainWindow):
    """Janela principal — Fase 1: esqueleto com abas e home screen."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyReaderPDF")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("QMainWindow { background:#1e1e1e; }")

        self._tab_counter = 0
        self._tab_paths   = {}   # tab index -> path

        self._build_ui()
        self._bind_shortcuts()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        # Toolbar
        self._toolbar = Toolbar(self)
        self.addToolBar(self._toolbar)
        self._connect_toolbar()

        # Status bar
        self._statusbar = Statusbar(self)
        self.setStatusBar(self._statusbar)

        # Tab widget central
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True)
        self._tabs.setStyleSheet(self._tab_style())
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tabs)

        # Home (aba permanente — sem botão de fechar)
        self._home = HomeScreen()
        self._home.open_requested.connect(self.open_path)
        self._tabs.addTab(self._home, "⌂  Início")
        from PySide6.QtWidgets import QTabBar
        self._tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)

        self._toolbar.set_pdf_enabled(False)

    def _connect_toolbar(self):
        self._toolbar.open_requested.connect(self.open_file)
        self._toolbar.prev_requested.connect(self.prev_page)
        self._toolbar.next_requested.connect(self.next_page)
        self._toolbar.go_to_requested.connect(self.go_to_page)
        self._toolbar.zoom_in_requested.connect(self.zoom_in)
        self._toolbar.zoom_out_requested.connect(self.zoom_out)
        self._toolbar.zoom_reset_requested.connect(self.zoom_reset)
        self._toolbar.view_mode_toggled.connect(self.toggle_view_mode)
        self._toolbar.add_library_requested.connect(self.add_active_to_library)

    def _bind_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self.duplicate_tab)
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self.close_active_tab)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.open_file)

    # ------------------------------------------------------------------ Abrir arquivo

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar PDF", "", "Arquivos PDF (*.pdf *.PDF)"
        )
        if path:
            self.open_path(path)

    def open_path(self, path: str):
        # Se já está aberto, só ativa a aba
        for i, p in self._tab_paths.items():
            if p == path:
                self._tabs.setCurrentIndex(i)
                return

        add_recent(path)
        add_to_library(path)
        self._home.refresh()
        self._open_tab(path)

    def _open_tab(self, path: str, title_suffix: str = ""):
        filename = path.replace("\\", "/").split("/")[-1]
        short    = filename if len(filename) <= 24 else filename[:21] + "..."
        if title_suffix:
            short += f" {title_suffix}"

        # Placeholder — será substituído por PDFTab na Fase 2
        placeholder = QWidget()
        placeholder.setStyleSheet("background:#1e1e1e;")

        idx = self._tabs.addTab(placeholder, short)
        self._tab_paths[idx] = path
        self._tabs.setCurrentIndex(idx)
        self._statusbar.set_message(f"Aberto: {filename}  (visualizador chega na Fase 2)")

    # ------------------------------------------------------------------ Duplicar aba

    def duplicate_tab(self):
        path = self._current_path()
        if not path:
            return
        filename = path.replace("\\", "/").split("/")[-1]
        short    = filename if len(filename) <= 24 else filename[:21] + "..."
        self._open_tab(path, title_suffix="(2)")
        self._statusbar.set_message(
            f"Aba duplicada — arraste para criar Split View")

    # ------------------------------------------------------------------ Gerenciar abas

    def _close_tab(self, index: int):
        if index == 0:
            return  # home não fecha
        self._tabs.removeTab(index)
        # Reindexar paths
        new_paths = {}
        for i in range(self._tabs.count()):
            old_idx = list(self._tab_paths.keys())
            # Mapeia pelo widget
            w = self._tabs.widget(i)
            for oi, p in self._tab_paths.items():
                if self._tabs.indexOf(w) == i:
                    new_paths[i] = p
        self._tab_paths = {
            i: p for i, p in self._tab_paths.items() if i != index
        }

    def close_active_tab(self):
        idx = self._tabs.currentIndex()
        if idx > 0:
            self._close_tab(idx)

    def _on_tab_changed(self, index: int):
        is_home = index == 0
        self._toolbar.set_pdf_enabled(not is_home)
        if is_home:
            self.setWindowTitle("PyReaderPDF")
            self._statusbar.set_message("Início")
        else:
            path = self._tab_paths.get(index, "")
            name = path.replace("\\", "/").split("/")[-1] if path else ""
            self.setWindowTitle(f"PyReaderPDF — {name}")

    def _current_path(self) -> str | None:
        idx = self._tabs.currentIndex()
        return self._tab_paths.get(idx)

    # ------------------------------------------------------------------ Ações (Fase 2 implementa de fato)

    def prev_page(self):         pass
    def next_page(self):         pass
    def go_to_page(self, p):     pass
    def zoom_in(self):           pass
    def zoom_out(self):          pass
    def zoom_reset(self):        pass
    def toggle_view_mode(self):  pass

    def add_active_to_library(self):
        path = self._current_path()
        if path:
            add_to_library(path)
            self._home.refresh()
            name = path.replace("\\", "/").split("/")[-1]
            self._statusbar.set_message(f"'{name}' adicionado à biblioteca")

    # ------------------------------------------------------------------ Estilo abas

    def _tab_style(self):
        return """
        QTabWidget::pane {
            border: none;
            background: #1e1e1e;
        }
        QTabBar {
            background: #141414;
        }
        QTabBar::tab {
            background: #2a2a2a;
            color: #999;
            padding: 7px 16px;
            margin-right: 1px;
            font-size: 9pt;
            min-width: 80px;
        }
        QTabBar::tab:selected {
            background: #1e1e1e;
            color: white;
            border-top: 2px solid #2980b9;
        }
        QTabBar::tab:hover:!selected {
            background: #333;
            color: #ccc;
        }
        QTabBar::close-button {
            image: none;
            subcontrol-position: right;
        }
        QTabBar::scroller {
            width: 20px;
        }
        """