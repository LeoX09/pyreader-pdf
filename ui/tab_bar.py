from PySide6.QtWidgets import QTabBar
from PySide6.QtCore import Qt, QPoint


class DraggableTabBar(QTabBar):
    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self._app      = app_ref
        self._drag_idx = -1
        self._start    = QPoint()
        self._dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_idx = self.tabAt(event.pos())
            self._start    = event.pos()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_idx > 0 and event.buttons() & Qt.MouseButton.LeftButton:
            dy = event.pos().y() - self._start.y()
            dl = (event.pos() - self._start).manhattanLength()
            if not self._dragging and dl > 15 and dy > 10:
                self._dragging = True
            if self._dragging:
                gp   = event.globalPosition().toPoint()
                side = self._app.global_pos_to_side(gp)
                self._app.show_drop_overlay(side)
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging and self._drag_idx > 0:
            self._dragging = False
            gp   = event.globalPosition().toPoint()
            side = self._app.global_pos_to_side(gp)
            self._app.hide_drop_overlay()
            self._app.create_split_from_drag(self._drag_idx, side)
            self._drag_idx = -1
            return
        self._dragging = False
        self._drag_idx = -1
        super().mouseReleaseEvent(event)