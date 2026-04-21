from PySide6.QtWidgets import (QWidget, QHBoxLayout, QPushButton,
                                QFrame, QStackedWidget)
from PySide6.QtCore import Signal, Qt

HIGHLIGHT_COLORS = [
    ("#f6c90e", "Amarelo"),
    ("#2ecc71", "Verde"),
    ("#e74c3c", "Vermelho"),
    ("#3498db", "Azul"),
    ("#e67e22", "Laranja"),
]

_BTN_BASE = """
    QPushButton {{
        background: {bg}; color: {fg}; border: none;
        border-radius: 4px; padding: 0 10px; font-size: 8pt;
    }}
    QPushButton:hover {{ background: {hbg}; color: white; }}
"""

_BAR_STYLE = """
    HighlightBar {
        background: #252525;
        border: 1px solid #444;
        border-radius: 8px;
    }
"""


def _sep():
    f = QFrame()
    f.setFixedSize(1, 22)
    f.setStyleSheet("background: #444;")
    return f


def _close_btn(signal):
    btn = QPushButton("×")
    btn.setFixedSize(24, 24)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("""
        QPushButton { background: transparent; color: #777; border: none; font-size: 14pt; }
        QPushButton:hover { color: white; }
    """)
    btn.clicked.connect(signal)
    return btn


class HighlightBar(QWidget):
    """
    Barra flutuante com dois modos:
    - Modo seleção: Copiar + escolha de cor para marcar
    - Modo remoção: botão para remover o highlight clicado
    """

    color_chosen     = Signal(str)   # hex color
    copy_requested   = Signal()
    note_requested   = Signal()
    dismissed        = Signal()
    remove_requested = Signal(int)   # highlight_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(_BAR_STYLE)
        self._pending_remove_id = -1
        self._build()
        self.hide()

    # ------------------------------------------------------------------ Build

    def _build(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_selection_page())
        self._stack.addWidget(self._build_remove_page())
        outer.addWidget(self._stack)

    def _build_selection_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(5)

        copy_btn = QPushButton("Copiar")
        copy_btn.setFixedHeight(26)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(_BTN_BASE.format(bg="#333", fg="#ddd", hbg="#4a4a4a"))
        copy_btn.clicked.connect(self.copy_requested)
        layout.addWidget(copy_btn)

        note_btn = QPushButton("📝 Nota")
        note_btn.setFixedHeight(26)
        note_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        note_btn.setStyleSheet(_BTN_BASE.format(bg="#1a2a3a", fg="#5dade2", hbg="#1e3a5a"))
        note_btn.clicked.connect(self.note_requested)
        layout.addWidget(note_btn)

        layout.addWidget(_sep())

        lbl = QPushButton("Marcador:")
        lbl.setEnabled(False)
        lbl.setFixedHeight(26)
        lbl.setStyleSheet(
            "QPushButton { background:transparent; color:#777; border:none; "
            "font-size:8pt; padding:0 4px; }")
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
                QPushButton:hover {{ border: 2px solid white; }}
            """)
            btn.clicked.connect(lambda checked, c=color: self.color_chosen.emit(c))
            layout.addWidget(btn)

        layout.addWidget(_sep())
        layout.addWidget(_close_btn(self.dismissed))
        return page

    def _build_remove_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(5)

        remove_btn = QPushButton("🗑  Remover marcação")
        remove_btn.setFixedHeight(26)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setStyleSheet(_BTN_BASE.format(bg="#3a1a1a", fg="#e74c3c", hbg="#5a2020"))
        remove_btn.clicked.connect(self._on_remove_clicked)
        layout.addWidget(remove_btn)

        layout.addWidget(_sep())
        layout.addWidget(_close_btn(self.dismissed))
        return page

    # ------------------------------------------------------------------ API pública

    def show_selection_mode(self):
        """Exibe a barra no modo de marcação de texto."""
        self._stack.setCurrentIndex(0)
        self.adjustSize()
        self.show()
        self.raise_()

    def show_remove_mode(self, highlight_id: int):
        """Exibe a barra no modo de remoção de highlight."""
        self._pending_remove_id = highlight_id
        self._stack.setCurrentIndex(1)
        self.adjustSize()
        self.show()
        self.raise_()

    def _on_remove_clicked(self):
        self.remove_requested.emit(self._pending_remove_id)
