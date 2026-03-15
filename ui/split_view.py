from PySide6.QtWidgets import QSplitter, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal


class PanelHeader(QWidget):
    close_requested = Signal()

    def __init__(self, filename: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setStyleSheet("background:#252525; border-bottom:1px solid #333;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 6, 0)

        lbl = QLabel(filename)
        lbl.setStyleSheet("color:#aaa; font-size:8pt; background:transparent;")
        layout.addWidget(lbl, stretch=1)

        btn = QPushButton("×")
        btn.setFixedSize(20, 20)
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:#555; border:none; font-size:13pt; }
            QPushButton:hover { color:#ff6b6b; }
        """)
        btn.clicked.connect(self.close_requested)
        layout.addWidget(btn)


class SplitPanel(QWidget):
    close_requested = Signal()

    def __init__(self, content: QWidget, filename: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = PanelHeader(filename, self)
        header.close_requested.connect(self.close_requested)
        layout.addWidget(header)
        layout.addWidget(content, stretch=1)


class SplitView(QSplitter):
    """Dois painéis lado a lado separados por divisor arrastável."""
    closed = Signal()

    def __init__(self, left: QWidget, right: QWidget,
                 left_name: str, right_name: str, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setHandleWidth(6)
        self.setChildrenCollapsible(False)
        self.setStyleSheet("""
            QSplitter::handle          { background:#2a2a2a; }
            QSplitter::handle:hover    { background:#2980b9; }
            QSplitter::handle:pressed  { background:#1a5c8a; }
        """)

        self._left_panel  = SplitPanel(left,  left_name,  self)
        self._right_panel = SplitPanel(right, right_name, self)
        self._left_panel.close_requested.connect(self.closed)
        self._right_panel.close_requested.connect(self.closed)

        self.addWidget(self._left_panel)
        self.addWidget(self._right_panel)
        self.setSizes([500, 500])