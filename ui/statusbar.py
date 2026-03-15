from PySide6.QtWidgets import QStatusBar, QLabel
from PySide6.QtCore import Qt


class Statusbar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QStatusBar {
                background: #2d2d2d;
                color: #888;
                font-size: 9pt;
                border-top: 1px solid #333;
            }
        """)
        self._label = QLabel("Bem-vindo ao PyReaderPDF")
        self._label.setStyleSheet("color:#888; padding: 0 8px;")
        self.addWidget(self._label)

    def update(self, current: int, total: int, zoom: float):
        self._label.setText(
            f"Página {current} de {total}  |  Zoom: {int(zoom * 100)}%"
        )

    def set_message(self, msg: str):
        self._label.setText(msg)