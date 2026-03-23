from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QFont


class DropOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._side = "none"

    def set_side(self, side: str):
        self._side = side
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()

        lc = QColor(26, 107, 60,  180 if self._side == "left"  else 70)
        rc = QColor(26,  79, 107, 180 if self._side == "right" else 70)
        p.fillRect(0, 0, w // 2, h, lc)
        p.fillRect(w // 2, 0, w // 2, h, rc)

        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 200))
        p.drawText(QRect(0,      0, w // 2, h), Qt.AlignmentFlag.AlignCenter, "◧  Esquerda")
        p.drawText(QRect(w // 2, 0, w // 2, h), Qt.AlignmentFlag.AlignCenter, "◨  Direita")
        p.end()