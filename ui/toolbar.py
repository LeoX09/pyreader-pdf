from PySide6.QtWidgets import QToolBar, QLabel, QLineEdit, QPushButton, QWidget, QSizePolicy
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIntValidator


class Toolbar(QToolBar):
    """Barra de ferramentas principal."""

    # Signals
    open_requested       = Signal()
    prev_requested       = Signal()
    next_requested       = Signal()
    go_to_requested      = Signal(int)
    zoom_in_requested    = Signal()
    zoom_out_requested   = Signal()
    zoom_reset_requested = Signal()
    view_mode_toggled    = Signal()
    add_library_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(False)
        self.setStyleSheet(self._style())
        self._build()

    # ------------------------------------------------------------------ Build

    def _build(self):
        def btn(text, signal, tooltip=""):
            b = QPushButton(text)
            b.setToolTip(tooltip)
            b.clicked.connect(signal)
            b.setFixedHeight(28)
            return b

        def sep():
            s = QWidget()
            s.setFixedWidth(1)
            s.setStyleSheet("background:#444;")
            self.addWidget(s)
            sp = QWidget()
            sp.setFixedWidth(6)
            self.addWidget(sp)

        # Abrir
        self.addWidget(btn("Abrir PDF", self.open_requested, "Abrir arquivo PDF"))
        sep()

        # Navegação
        self.btn_prev = btn("◀", self.prev_requested, "Página anterior")
        self.btn_next = btn("▶", self.next_requested, "Próxima página")
        self.addWidget(self.btn_prev)
        self.addWidget(self.btn_next)
        sep()

        # Campo de página
        self.addWidget(QLabel("  Pág."))
        self._page_edit = QLineEdit()
        self._page_edit.setFixedWidth(48)
        self._page_edit.setAlignment(Qt.AlignCenter)
        self._page_edit.setValidator(QIntValidator(1, 99999))
        self._page_edit.returnPressed.connect(self._on_go_to)
        self.addWidget(self._page_edit)

        self._total_label = QLabel("/ -  ")
        self.addWidget(self._total_label)
        sep()

        # Zoom
        self.btn_zoom_out   = btn("−",    self.zoom_out_requested,   "Zoom out  (Ctrl+Scroll)")
        self.btn_zoom_reset = btn("100%", self.zoom_reset_requested,  "Zoom 100%")
        self.btn_zoom_in    = btn("+",    self.zoom_in_requested,    "Zoom in  (Ctrl+Scroll)")
        self.addWidget(self.btn_zoom_out)
        self.addWidget(self.btn_zoom_reset)
        self.addWidget(self.btn_zoom_in)
        sep()

        # Modo de visualização
        self.btn_view = btn("☰ Contínuo", self.view_mode_toggled, "Alternar modo contínuo / página única")
        self.addWidget(self.btn_view)
        sep()

        # Biblioteca
        self.addWidget(btn("+ Biblioteca", self.add_library_requested, "Adicionar à biblioteca"))

        # Espaço flexível + dica de atalhos
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)
        hint = QLabel("Ctrl+D  duplicar  |  Drag aba → Split View  |  Ctrl+W  fechar split  ")
        hint.setStyleSheet("color: #444; font-size: 8pt;")
        self.addWidget(hint)

        self._set_pdf_widgets([
            self.btn_prev, self.btn_next, self._page_edit,
            self.btn_zoom_in, self.btn_zoom_out, self.btn_zoom_reset,
            self.btn_view,
        ])

    # ------------------------------------------------------------------ API pública

    def set_pdf_enabled(self, enabled: bool):
        for w in self._pdf_widgets:
            w.setEnabled(enabled)
        if not enabled:
            self._page_edit.clear()
            self._total_label.setText("/ -  ")

    def update_page(self, current: int, total: int):
        self._page_edit.setText(str(current))
        self._total_label.setText(f"/ {total}  ")

    def set_view_mode(self, mode: str):
        if mode == "continuous":
            self.btn_view.setText("☰ Contínuo ✓")
            self.btn_view.setProperty("active", True)
        else:
            self.btn_view.setText("☰ Contínuo")
            self.btn_view.setProperty("active", False)
        self.btn_view.style().unpolish(self.btn_view)
        self.btn_view.style().polish(self.btn_view)

    # ------------------------------------------------------------------ Internos

    def _set_pdf_widgets(self, widgets):
        self._pdf_widgets = widgets

    def _on_go_to(self):
        try:
            page = int(self._page_edit.text())
            self.go_to_requested.emit(page)
        except ValueError:
            pass

    # ------------------------------------------------------------------ Estilo

    def _style(self):
        return """
        QToolBar {
            background: #2d2d2d;
            border: none;
            padding: 4px 6px;
            spacing: 3px;
        }
        QPushButton {
            background: #3a3a3a;
            color: #e0e0e0;
            border: none;
            border-radius: 4px;
            padding: 3px 10px;
            font-size: 9pt;
        }
        QPushButton:hover    { background: #505050; }
        QPushButton:pressed  { background: #222; }
        QPushButton:disabled { color: #555; background: #2a2a2a; }
        QPushButton[active=true] { background: #1a4f6b; }
        QLineEdit {
            background: #3a3a3a;
            color: #e0e0e0;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 9pt;
        }
        QLabel { color: #aaa; font-size: 9pt; background: transparent; }
        """