from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QWidget, QDoubleSpinBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

import core.config as config


class SettingRow(QWidget):
    """Uma linha de configuração com label à esquerda e controle à direita."""
    def __init__(self, label: str, description: str, control: QWidget, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)

        text = QWidget()
        text.setStyleSheet("background:transparent;")
        tl = QVBoxLayout(text)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(2)

        lbl = QLabel(label)
        lbl.setStyleSheet("color:#e0e0e0; font-size:10pt; font-weight:500; background:transparent;")
        desc = QLabel(description)
        desc.setStyleSheet("color:#666; font-size:8pt; background:transparent;")
        tl.addWidget(lbl)
        tl.addWidget(desc)

        layout.addWidget(text, stretch=1)
        layout.addWidget(control)


class SectionLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            color: #2980b9;
            font-size: 8pt;
            font-weight: bold;
            letter-spacing: 1px;
            background: transparent;
            padding: 16px 0 6px 0;
        """)


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet("background:#2a2a2a;")


class SettingsDialog(QDialog):
    """Painel de configurações."""
    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.setFixedSize(520, 480)
        self.setStyleSheet("""
            QDialog {
                background: #1a1a1a;
                border: 1px solid #333;
                border-radius: 8px;
            }
        """)
        self._cfg = config.load()
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("background:#141414; border-bottom:1px solid #2a2a2a;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 16, 0)
        title = QLabel("Configurações")
        title.setStyleSheet("color:white; font-size:14pt; font-weight:bold; background:transparent;")
        hl.addWidget(title, stretch=1)
        btn_close = QPushButton("×")
        btn_close.setFixedSize(32, 32)
        btn_close.setStyleSheet("""
            QPushButton { background:transparent; color:#666; border:none; font-size:18pt; }
            QPushButton:hover { color:#ff6b6b; }
        """)
        btn_close.clicked.connect(self.reject)
        hl.addWidget(btn_close)
        layout.addWidget(header)

        # Scroll area com conteúdo
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:#1a1a1a; }")
        content = QWidget()
        content.setStyleSheet("background:#1a1a1a;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 8, 24, 24)
        cl.setSpacing(0)

        # ---- Seção: Visualização ----
        cl.addWidget(SectionLabel("VISUALIZAÇÃO"))
        cl.addWidget(Divider())

        self._view_combo = QComboBox()
        self._view_combo.addItem("Contínuo (recomendado)", "continuous")
        self._view_combo.addItem("Página única",           "single")
        idx = 0 if self._cfg.get("view_mode") == "continuous" else 1
        self._view_combo.setCurrentIndex(idx)
        self._style_combo(self._view_combo)
        cl.addWidget(SettingRow(
            "Modo de visualização",
            "Define como os PDFs são exibidos ao abrir",
            self._view_combo
        ))
        cl.addWidget(Divider())

        self._zoom_spin = QDoubleSpinBox()
        self._zoom_spin.setRange(0.5, 4.0)
        self._zoom_spin.setSingleStep(0.25)
        self._zoom_spin.setDecimals(2)
        self._zoom_spin.setValue(self._cfg.get("default_zoom", 1.5))
        self._zoom_spin.setFixedWidth(90)
        self._zoom_spin.setStyleSheet("""
            QDoubleSpinBox {
                background:#2a2a2a; color:#e0e0e0;
                border:1px solid #444; border-radius:4px;
                padding:4px 8px; font-size:10pt;
            }
        """)
        cl.addWidget(SettingRow(
            "Zoom padrão",
            "Nível de zoom ao abrir um novo PDF",
            self._zoom_spin
        ))

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        # Footer com botões
        footer = QWidget()
        footer.setFixedHeight(60)
        footer.setStyleSheet("background:#141414; border-top:1px solid #2a2a2a;")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 0, 24, 0)
        fl.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFixedSize(100, 32)
        btn_cancel.setStyleSheet("""
            QPushButton { background:#2a2a2a; color:#aaa; border:none; border-radius:4px; font-size:9pt; }
            QPushButton:hover { background:#333; color:white; }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Salvar")
        btn_save.setFixedSize(100, 32)
        btn_save.setStyleSheet("""
            QPushButton { background:#2980b9; color:white; border:none; border-radius:4px; font-size:9pt; font-weight:bold; }
            QPushButton:hover { background:#3498db; }
        """)
        btn_save.clicked.connect(self._save)

        fl.addWidget(btn_cancel)
        fl.addSpacing(8)
        fl.addWidget(btn_save)
        layout.addWidget(footer)

    def _style_combo(self, combo: QComboBox):
        combo.setFixedWidth(200)
        combo.setStyleSheet("""
            QComboBox {
                background:#2a2a2a; color:#e0e0e0;
                border:1px solid #444; border-radius:4px;
                padding:4px 12px; font-size:10pt;
                min-height:28px;
            }
            QComboBox:hover { border-color:#555; }
            QComboBox::drop-down { border:none; width:24px; }
            QComboBox::down-arrow { image:none; }
            QComboBox QAbstractItemView {
                background:#2a2a2a; color:#e0e0e0;
                border:1px solid #444; selection-background-color:#2980b9;
            }
        """)

    def _save(self):
        config.set("view_mode",    self._view_combo.currentData())
        config.set("default_zoom", self._zoom_spin.value())
        self.settings_changed.emit()
        self.accept()