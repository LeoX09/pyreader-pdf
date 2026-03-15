from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject
from PySide6.QtGui import QColor, QPen, QPainter, QCursor


class TextLayerSignals(QObject):
    text_selected = Signal(str, int)   # text, page_index


class WordRect:
    __slots__ = ("text", "rect")
    def __init__(self, text: str, rect: QRectF):
        self.text = text
        self.rect = rect


class TextLayer(QGraphicsItem):
    """
    Camada transparente sobre a página.
    - Cursor muda para IBeam SOMENTE quando passa sobre uma palavra
    - Seleção por drag entre palavras
    """

    def __init__(self, page_rect: QRectF, words: list,
                 page_index: int, signals: TextLayerSignals):
        super().__init__()
        self._rect       = page_rect
        self._words      = words
        self._page_index = page_index
        self._signals    = signals
        self._selected   = set()
        self._drag_start = None
        self._drag_rect  = QRectF()
        self._on_text    = False   # cursor está sobre uma palavra?

        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    # ------------------------------------------------------------------ Qt

    def boundingRect(self) -> QRectF:
        return self._rect

    def paint(self, painter: QPainter, option, widget=None):
        for i in self._selected:
            w = self._words[i]
            painter.fillRect(w.rect, QColor(41, 128, 185, 90))

        if not self._drag_rect.isNull():
            painter.setPen(QPen(QColor(41, 128, 185, 160), 1))
            painter.fillRect(self._drag_rect, QColor(41, 128, 185, 25))
            painter.drawRect(self._drag_rect)

    # ------------------------------------------------------------------ Hover

    def _word_at(self, pos: QPointF) -> int | None:
        """Retorna o índice da palavra sob o ponto, ou None."""
        for i, w in enumerate(self._words):
            if w.rect.contains(pos):
                return i
        return None

    def hoverMoveEvent(self, event):
        on_word = self._word_at(event.pos()) is not None
        if on_word != self._on_text:
            self._on_text = on_word
            self.setCursor(
                Qt.CursorShape.IBeamCursor if on_word
                else Qt.CursorShape.ArrowCursor
            )

    def hoverLeaveEvent(self, event):
        self._on_text = False
        self.setCursor(Qt.CursorShape.ArrowCursor)

    # ------------------------------------------------------------------ Mouse

    def mousePressEvent(self, event):
        self._drag_start = event.pos()
        self._selected.clear()
        self._drag_rect  = QRectF()
        self.update()

    def mouseMoveEvent(self, event):
        if self._drag_start is None:
            return
        self._drag_rect = QRectF(self._drag_start, event.pos()).normalized()
        self._selected  = {
            i for i, w in enumerate(self._words)
            if self._drag_rect.intersects(w.rect)
        }
        self.update()

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        self._drag_rect  = QRectF()
        if self._selected:
            ordered = sorted(self._selected,
                             key=lambda i: (self._words[i].rect.y(),
                                            self._words[i].rect.x()))
            text = " ".join(self._words[i].text for i in ordered)
            self._signals.text_selected.emit(text, self._page_index)
        self.update()

    def clear_selection(self):
        self._selected.clear()
        self.update()