from PySide6.QtWidgets import (QToolBar, QLabel, QLineEdit, QPushButton,
                                QWidget, QSizePolicy, QFrame)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIntValidator, QFont


class Toolbar(QToolBar):

    open_requested        = Signal()
    prev_requested        = Signal()
    next_requested        = Signal()
    go_to_requested       = Signal(int)
    zoom_in_requested     = Signal()
    zoom_out_requested    = Signal()
    zoom_reset_requested  = Signal()
    settings_requested    = Signal()
    add_library_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(False)
        self.setStyleSheet(self._style())
        self._pdf_widgets = []
        self._build()

    def _build(self):
        def btn(text, signal=None, tooltip="", width=None, accent=False):
            b = QPushButton(text)
            b.setToolTip(tooltip)
            if signal:
                b.clicked.connect(signal)
            b.setFixedHeight(30)
            if width:
                b.setFixedWidth(width)
            if accent:
                b.setProperty("accent", True)
            return b

        def sep():
            f = QFrame()
            f.setFixedSize(1, 20)
            f.setStyleSheet("background:#3a3a3a;")
            self.addWidget(f)
            sp = QWidget()
            sp.setFixedWidth(4)
            self.addWidget(sp)

        sp_left = QWidget()
        sp_left.setFixedWidth(6)
        self.addWidget(sp_left)

        # Abrir
        b_open = btn("📂  Abrir", self.open_requested, "Abrir PDF  (Ctrl+O)", width=90)
        self.addWidget(b_open)

        sep()

        # Navegação
        self.btn_prev = btn("‹", self.prev_requested, "Página anterior", width=30)
        self.btn_next = btn("›", self.next_requested, "Próxima página",  width=30)
        self.addWidget(self.btn_prev)

        # Campo de página
        self._page_edit = QLineEdit()
        self._page_edit.setFixedSize(46, 30)
        self._page_edit.setAlignment(Qt.AlignCenter)
        self._page_edit.setValidator(QIntValidator(1, 99999))
        self._page_edit.returnPressed.connect(self._on_go_to)
        self._page_edit.setToolTip("Ir para página")
        self.addWidget(self._page_edit)

        self.addWidget(self.btn_next)

        self._total_label = QLabel("/  —")
        self._total_label.setStyleSheet("color:#555; font-size:9pt; background:transparent; padding:0 6px;")
        self.addWidget(self._total_label)

        sep()

        # Zoom
        self.btn_zoom_out   = btn("−", self.zoom_out_requested,  "Zoom −", width=30)
        self._zoom_label    = QLabel("100%")
        self._zoom_label.setFixedWidth(44)
        self._zoom_label.setAlignment(Qt.AlignCenter)
        self._zoom_label.setStyleSheet("color:#aaa; font-size:9pt; background:transparent; cursor:pointer;")
        self._zoom_label.mousePressEvent = lambda e: self.zoom_reset_requested.emit()
        self._zoom_label.setToolTip("Clique para resetar zoom")
        self.btn_zoom_in    = btn("+", self.zoom_in_requested,   "Zoom +", width=30)
        self.addWidget(self.btn_zoom_out)
        self.addWidget(self._zoom_label)
        self.addWidget(self.btn_zoom_in)

        sep()

        # Biblioteca
        b_lib = btn("＋  Biblioteca", self.add_library_requested,
                    "Adicionar à biblioteca", width=120)
        self.addWidget(b_lib)

        # Espaço flexível
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)

        # Dica de atalhos
        hint = QLabel("Ctrl+D  duplicar   Ctrl+→/←  split   Esc  fechar split")
        hint.setStyleSheet("color:#333; font-size:8pt; background:transparent; padding-right:12px;")
        self.addWidget(hint)

        sep()

        # Configurações
        b_settings = btn("⚙", self.settings_requested, "Configurações", width=34)
        b_settings.setProperty("icon_btn", True)
        self.addWidget(b_settings)

        sp_right = QWidget()
        sp_right.setFixedWidth(4)
        self.addWidget(sp_right)

        self._pdf_widgets = [
            self.btn_prev, self.btn_next, self._page_edit,
            self.btn_zoom_in, self.btn_zoom_out, self._zoom_label,
        ]

    # ------------------------------------------------------------------ API

    def set_pdf_enabled(self, enabled: bool):
        for w in self._pdf_widgets:
            w.setEnabled(enabled)
        if not enabled:
            self._page_edit.clear()
            self._total_label.setText("/  —")
            self._zoom_label.setText("—")

    def update_page(self, current: int, total: int):
        self._page_edit.setText(str(current))
        self._total_label.setText(f"/  {total}")

    def update_zoom(self, zoom: float):
        self._zoom_label.setText(f"{int(zoom * 100)}%")

    def _on_go_to(self):
        try:
            self.go_to_requested.emit(int(self._page_edit.text()))
        except ValueError:
            pass

    # ------------------------------------------------------------------ Estilo

    def _style(self):
        return """
        QToolBar {
            background: #1a1a1a;
            border-bottom: 1px solid #2a2a2a;
            padding: 4px 0;
            spacing: 3px;
        }
        QPushButton {
            background: #242424;
            color: #c8c8c8;
            border: 1px solid #333;
            border-radius: 5px;
            padding: 0 10px;
            font-size: 9pt;
        }
        QPushButton:hover   { background:#2e2e2e; border-color:#444; color:white; }
        QPushButton:pressed { background:#1a1a1a; }
        QPushButton:disabled{ color:#444; background:#1e1e1e; border-color:#2a2a2a; }
        QPushButton[accent=true]  { background:#1a4f6b; border-color:#2980b9; color:white; }
        QPushButton[accent=true]:hover { background:#1f6080; }
        QPushButton[icon_btn=true] { font-size:13pt; padding:0; }
        QLineEdit {
            background: #242424;
            color: #e0e0e0;
            border: 1px solid #333;
            border-radius: 5px;
            padding: 2px 4px;
            font-size: 9pt;
        }
        QLineEdit:focus { border-color:#2980b9; }
        """