import fitz
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QToolTip
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject
from PySide6.QtGui import QColor, QPen, QBrush, QPainter, QCursor


class TextLayerSignals(QObject):
    text_selected = Signal(str, int)   # text, page_index


class WordRect:
    """Palavra com sua bbox em coords de scene (zoom=1.0)."""
    __slots__ = ("text", "rect")
    def __init__(self, text: str, rect: QRectF):
        self.text = text
        self.rect = rect


class TextLayer(QGraphicsItem):
    """
    Camada transparente sobre uma página que:
    - Detecta hover (muda cursor para IBeam)
    - Permite seleção de palavras por drag
    - Emite text_selected com o texto selecionado
    """

    def __init__(self, page_rect: QRectF, words: list[WordRect],
                 page_index: int, signals: TextLayerSignals):
        super().__init__()
        self._rect       = page_rect
        self._words      = words
        self._page_index = page_index
        self._signals    = signals
        self._selected   = set()   # índices de palavras selecionadas
        self._drag_start = None
        self._drag_rect  = QRectF()

        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setCursor(Qt.CursorShape.IBeamCursor)

    # ------------------------------------------------------------------ Qt overrides

    def boundingRect(self) -> QRectF:
        return self._rect

    def paint(self, painter: QPainter, option, widget=None):
        # Highlights das palavras selecionadas
        for i in self._selected:
            w = self._words[i]
            painter.fillRect(w.rect, QColor(41, 128, 185, 80))

        # Retângulo de drag em curso
        if not self._drag_rect.isNull():
            painter.setPen(QPen(QColor(41, 128, 185, 160), 1))
            painter.fillRect(self._drag_rect, QColor(41, 128, 185, 30))
            painter.drawRect(self._drag_rect)

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
        # Seleciona palavras que intersectam o drag rect
        self._selected.clear()
        for i, w in enumerate(self._words):
            if self._drag_rect.intersects(w.rect):
                self._selected.add(i)
        self.update()

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        self._drag_rect  = QRectF()
        if self._selected:
            # Ordena por posição (top→bottom, left→right)
            ordered = sorted(self._selected,
                             key=lambda i: (self._words[i].rect.y(),
                                            self._words[i].rect.x()))
            text = " ".join(self._words[i].text for i in ordered)
            self._signals.text_selected.emit(text, self._page_index)
        self.update()

    def hoverEnterEvent(self, event):
        self.setCursor(Qt.CursorShape.IBeamCursor)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def clear_selection(self):
        self._selected.clear()
        self.update()


def build_word_rects(fitz_page, scale: float = 1.0) -> list[WordRect]:
    """
    Extrai palavras de uma página PyMuPDF e retorna WordRect em coords de scene.
    scale=1.0 para scene em PDF points.
    """
    words = []
    for w in fitz_page.get_text("words"):
        x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
        rect = QRectF(x0 * scale, y0 * scale,
                      (x1 - x0) * scale, (y1 - y0) * scale)
        words.append(WordRect(text, rect))
    return words