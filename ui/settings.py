from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, Signal

from qfluentwidgets import (
    MessageBoxBase, SubtitleLabel, BodyLabel, CaptionLabel,
    ComboBox, DoubleSpinBox, FluentIcon as FI,
    CardWidget, SwitchButton
)

import core.config as config


class SettingsDialog(MessageBoxBase):
    """Painel de configurações com Fluent Design."""
    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg = config.load()
        self._build()

    def _build(self):
        self.titleLabel = SubtitleLabel("Configurações", self)
        self.viewLayout.addWidget(self.titleLabel)

        # ---- Modo de visualização ----
        row1 = CardWidget()
        rl1  = QHBoxLayout(row1)
        rl1.setContentsMargins(16, 12, 16, 12)

        info1 = QWidget()
        il1   = QVBoxLayout(info1)
        il1.setContentsMargins(0, 0, 0, 0)
        il1.addWidget(BodyLabel("Modo de visualização"))
        il1.addWidget(CaptionLabel("Define como os PDFs são exibidos ao abrir"))
        rl1.addWidget(info1, stretch=1)

        self._view_combo = ComboBox()
        self._view_combo.addItem("Contínuo (recomendado)", userData="continuous")
        self._view_combo.addItem("Página única",           userData="single")
        self._view_combo.setCurrentIndex(
            0 if self._cfg.get("view_mode") == "continuous" else 1)
        self._view_combo.setFixedWidth(200)
        rl1.addWidget(self._view_combo)
        self.viewLayout.addWidget(row1)

        # ---- Zoom padrão ----
        row2 = CardWidget()
        rl2  = QHBoxLayout(row2)
        rl2.setContentsMargins(16, 12, 16, 12)

        info2 = QWidget()
        il2   = QVBoxLayout(info2)
        il2.setContentsMargins(0, 0, 0, 0)
        il2.addWidget(BodyLabel("Zoom padrão"))
        il2.addWidget(CaptionLabel("Nível de zoom ao abrir um novo PDF"))
        rl2.addWidget(info2, stretch=1)

        self._zoom_spin = DoubleSpinBox()
        self._zoom_spin.setRange(0.5, 4.0)
        self._zoom_spin.setSingleStep(0.25)
        self._zoom_spin.setDecimals(2)
        self._zoom_spin.setValue(self._cfg.get("default_zoom", 1.5))
        self._zoom_spin.setFixedWidth(100)
        rl2.addWidget(self._zoom_spin)
        self.viewLayout.addWidget(row2)

        # Botões
        self.yesButton.setText("Salvar")
        self.cancelButton.setText("Cancelar")
        self.widget.setMinimumWidth(480)

    def validate(self):
        config.set("view_mode",    self._view_combo.currentData())
        config.set("default_zoom", self._zoom_spin.value())
        self.settings_changed.emit()
        return True