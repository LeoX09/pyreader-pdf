from PySide6.QtWidgets import QToolBar, QWidget, QSizePolicy, QFrame, QLabel
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIntValidator

from qfluentwidgets import (
    ToolButton, TransparentToolButton, LineEdit,
    FluentIcon as FI, CaptionLabel, BodyLabel
)


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
        self.setStyleSheet("""
            QToolBar {
                background: #141414;
                border-bottom: 1px solid #2a2a2a;
                padding: 4px 0;
                spacing: 2px;
            }
        """)
        self._pdf_widgets = []
        self._build()

    def _build(self):
        def sp(w=6):
            s = QWidget(); s.setFixedWidth(w)
            self.addWidget(s)

        def sep():
            f = QFrame(); f.setFixedSize(1, 20)
            f.setStyleSheet("background:#333;")
            self.addWidget(f)
            sp(4)

        sp()

        # Abrir
        btn_open = ToolButton(FI.FOLDER)
        btn_open.setToolTip("Abrir PDF  (Ctrl+O)")
        btn_open.clicked.connect(self.open_requested)
        self.addWidget(btn_open)
        sp(2)

        lbl_open = BodyLabel("Abrir")
        lbl_open.setStyleSheet("background:transparent;padding-right:4px;")
        self.addWidget(lbl_open)

        sep()

        # Navegação
        self.btn_prev = ToolButton(FI.LEFT_ARROW)
        self.btn_prev.setToolTip("Página anterior")
        self.btn_prev.clicked.connect(self.prev_requested)
        self.addWidget(self.btn_prev)

        self._page_edit = LineEdit()
        self._page_edit.setFixedSize(52, 30)
        self._page_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_edit.setValidator(QIntValidator(1, 99999))
        self._page_edit.returnPressed.connect(self._on_go_to)
        self._page_edit.setToolTip("Ir para página")
        self.addWidget(self._page_edit)

        self.btn_next = ToolButton(FI.RIGHT_ARROW)
        self.btn_next.setToolTip("Próxima página")
        self.btn_next.clicked.connect(self.next_requested)
        self.addWidget(self.btn_next)

        self._total_label = CaptionLabel("/  —")
        self._total_label.setStyleSheet("background:transparent;padding:0 6px;")
        self.addWidget(self._total_label)

        sep()

        # Zoom
        self.btn_zoom_out = ToolButton(FI.ZOOM_OUT)
        self.btn_zoom_out.setToolTip("Zoom −")
        self.btn_zoom_out.clicked.connect(self.zoom_out_requested)
        self.addWidget(self.btn_zoom_out)

        self._zoom_label = BodyLabel("100%")
        self._zoom_label.setFixedWidth(48)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setStyleSheet("background:transparent;cursor:pointer;")
        self._zoom_label.setToolTip("Clique para resetar zoom")
        self._zoom_label.mousePressEvent = lambda e: self.zoom_reset_requested.emit()
        self.addWidget(self._zoom_label)

        self.btn_zoom_in = ToolButton(FI.ZOOM_IN)
        self.btn_zoom_in.setToolTip("Zoom +")
        self.btn_zoom_in.clicked.connect(self.zoom_in_requested)
        self.addWidget(self.btn_zoom_in)

        sep()

        # Biblioteca
        btn_lib = ToolButton(FI.ADD)
        btn_lib.setToolTip("Adicionar à biblioteca")
        btn_lib.clicked.connect(self.add_library_requested)
        self.addWidget(btn_lib)
        sp(2)
        lbl_lib = BodyLabel("Biblioteca")
        lbl_lib.setStyleSheet("background:transparent;padding-right:4px;")
        self.addWidget(lbl_lib)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)

        sep()

        # Configurações
        btn_settings = ToolButton(FI.SETTING)
        btn_settings.setToolTip("Configurações")
        btn_settings.clicked.connect(self.settings_requested)
        self.addWidget(btn_settings)
        sp(4)

        self._pdf_widgets = [
            self.btn_prev, self.btn_next, self._page_edit,
            self.btn_zoom_in, self.btn_zoom_out,
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