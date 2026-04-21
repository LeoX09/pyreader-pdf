from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFrame
from PySide6.QtCore import Signal, Qt

HIGHLIGHT_COLORS = [
    ("#f6c90e", "Amarelo"),
    ("#2ecc71", "Verde"),
    ("#e74c3c", "Vermelho"),
    ("#3498db", "Azul"),
    ("#e67e22", "Laranja"),
]


class HighlightBar(QWidget):
    """Barra flutuante que aparece após seleção de texto."""

    color_chosen   = Signal(str)   # hex color
    copy_requested = Signal()
    dismissed      = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            HighlightBar {
                background: #252525;
                border: 1px solid #444;
                border-radius: 8px;
            }
        """)
        self._build()
        self.hide()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(5)

        copy_btn = QPushButton("Copiar")
        copy_btn.setFixedHeight(26)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: #333; color: #ddd; border: none;
                border-radius: 4px; padding: 0 10px; font-size: 8pt;
            }
            QPushButton:hover { background: #4a4a4a; color: white; }
        """)
        copy_btn.clicked.connect(self.copy_requested)
        layout.addWidget(copy_btn)

        sep = QFrame()
        sep.setFixedSize(1, 22)
        sep.setStyleSheet("background: #444;")
        layout.addWidget(sep)

        lbl = QPushButton("Marcador:")
        lbl.setEnabled(False)
        lbl.setFixedHeight(26)
        lbl.setStyleSheet("""
            QPushButton {
                background: transparent; color: #777; border: none;
                font-size: 8pt; padding: 0 4px;
            }
        """)
        layout.addWidget(lbl)

        for color, name in HIGHLIGHT_COLORS:
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setToolTip(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color}; border: 2px solid transparent;
                    border-radius: 11px;
                }}
                QPushButton:hover {{
                    border: 2px solid white;
                }}
            """)
            btn.clicked.connect(lambda checked, c=color: self.color_chosen.emit(c))
            layout.addWidget(btn)

        sep2 = QFrame()
        sep2.setFixedSize(1, 22)
        sep2.setStyleSheet("background: #444;")
        layout.addWidget(sep2)

        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #777; border: none;
                font-size: 14pt;
            }
            QPushButton:hover { color: white; }
        """)
        close_btn.clicked.connect(self.dismissed)
        layout.addWidget(close_btn)

        self.adjustSize()
