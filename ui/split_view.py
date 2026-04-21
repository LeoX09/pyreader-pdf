from PySide6.QtWidgets import (QSplitter, QWidget, QVBoxLayout, QHBoxLayout,
                                QPushButton, QLabel, QLineEdit, QFrame)
from PySide6.QtCore import Qt, Signal

_NAV_BTN = """
    QPushButton {
        background: #333; color: #aaa; border: none;
        border-radius: 3px; font-size: 13pt; padding: 0;
    }
    QPushButton:hover { background: #444; color: white; }
    QPushButton:pressed { background: #2980b9; color: white; }
"""

_PAGE_INPUT = """
    QLineEdit {
        background: #1a1a1a; color: #ccc;
        border: 1px solid #383838; border-radius: 3px;
        font-size: 8pt; padding: 0 2px;
    }
    QLineEdit:focus { border-color: #2980b9; }
"""


class PanelHeader(QWidget):
    """
    Cabeçalho de cada painel do Split View.
    Exibe nome do arquivo, controles de navegação e botão fechar.
    """
    prev_requested  = Signal()
    next_requested  = Signal()
    go_to_requested = Signal(int)
    close_requested = Signal()

    def __init__(self, filename: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setStyleSheet("background:#252525; border-bottom:1px solid #333;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 6, 0)
        layout.setSpacing(5)

        self._name_lbl = QLabel(filename)
        self._name_lbl.setStyleSheet(
            "color:#aaa; font-size:8pt; background:transparent;")
        layout.addWidget(self._name_lbl, stretch=1)

        # ---- Navegação ----
        self._btn_prev = QPushButton("‹")
        self._btn_prev.setFixedSize(22, 22)
        self._btn_prev.setToolTip("Página anterior")
        self._btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_prev.setStyleSheet(_NAV_BTN)
        self._btn_prev.clicked.connect(self.prev_requested)
        layout.addWidget(self._btn_prev)

        self._page_input = QLineEdit("1")
        self._page_input.setFixedSize(38, 22)
        self._page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_input.setStyleSheet(_PAGE_INPUT)
        self._page_input.returnPressed.connect(self._on_go_to)
        layout.addWidget(self._page_input)

        self._total_lbl = QLabel("/ 1")
        self._total_lbl.setStyleSheet(
            "color:#555; font-size:8pt; background:transparent; min-width:32px;")
        layout.addWidget(self._total_lbl)

        self._btn_next = QPushButton("›")
        self._btn_next.setFixedSize(22, 22)
        self._btn_next.setToolTip("Próxima página")
        self._btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_next.setStyleSheet(_NAV_BTN)
        self._btn_next.clicked.connect(self.next_requested)
        layout.addWidget(self._btn_next)

        sep = QFrame()
        sep.setFixedSize(1, 18)
        sep.setStyleSheet("background:#444;")
        layout.addWidget(sep)

        btn_close = QPushButton("×")
        btn_close.setFixedSize(22, 22)
        btn_close.setToolTip("Fechar Split View")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton { background:transparent; color:#555; border:none; font-size:13pt; }
            QPushButton:hover { color:#ff6b6b; }
        """)
        btn_close.clicked.connect(self.close_requested)
        layout.addWidget(btn_close)

    def update_page(self, current: int, total: int):
        self._page_input.setText(str(current))
        self._total_lbl.setText(f"/ {total}")

    def _on_go_to(self):
        try:
            page = int(self._page_input.text())
            self.go_to_requested.emit(page)
        except ValueError:
            pass


class SplitPanel(QWidget):
    """Painel individual do Split View: cabeçalho com navegação + conteúdo."""
    close_requested = Signal()

    def __init__(self, content, filename: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._header  = PanelHeader(filename, self)
        self._content = content

        # Conecta controles → PDFTab
        self._header.close_requested.connect(self.close_requested)
        self._header.prev_requested.connect(content.prev_page)
        self._header.next_requested.connect(content.next_page)
        self._header.go_to_requested.connect(content.go_to)

        # Atualiza cabeçalho quando a página muda
        content.page_changed.connect(self._header.update_page)

        layout.addWidget(self._header)
        layout.addWidget(content, stretch=1)

        # Estado inicial
        self._header.update_page(content.current_page, content.total_pages)


class SplitView(QSplitter):
    """Dois painéis lado a lado separados por divisor arrastável."""
    closed = Signal()

    def __init__(self, left, right,
                 left_name: str, right_name: str, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setHandleWidth(6)
        self.setChildrenCollapsible(False)
        self.setStyleSheet("""
            QSplitter::handle         { background:#2a2a2a; }
            QSplitter::handle:hover   { background:#2980b9; }
            QSplitter::handle:pressed { background:#1a5c8a; }
        """)

        self._left_panel  = SplitPanel(left,  left_name,  self)
        self._right_panel = SplitPanel(right, right_name, self)
        self._left_panel.close_requested.connect(self.closed)
        self._right_panel.close_requested.connect(self.closed)

        self.addWidget(self._left_panel)
        self.addWidget(self._right_panel)
        self.setSizes([500, 500])
