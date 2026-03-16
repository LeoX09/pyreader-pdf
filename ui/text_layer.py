from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject, QTimer
from PySide6.QtGui import QColor, QPainter, QCursor


class TextLayerSignals(QObject):
    text_selected = Signal(str, int)   # text, page_index


class WordRect:
    __slots__ = ("text", "rect")
    def __init__(self, text: str, rect: QRectF):
        self.text = text
        self.rect = rect


class TextLayer(QGraphicsItem):
    """
    Camada de seleção de texto:
    - Clique simples + drag   → seleciona palavras arrastadas
    - Clique duplo            → seleciona a palavra inteira
    - Clique triplo           → seleciona a linha inteira
    - Cursor IBeam apenas sobre palavras
    """

    CLICK_INTERVAL = 300   # ms para detectar double/triple click

    def __init__(self, page_rect: QRectF, words: list,
                 page_index: int, signals: TextLayerSignals):
        super().__init__()
        self._rect        = page_rect
        self._words       = words
        self._page_index  = page_index
        self._signals     = signals
        self._selected    = set()
        self._drag_start  = None
        self._drag_rect   = QRectF()
        self._on_text     = False
        self._click_count = 0
        self._last_pos    = QPointF()
        self._multi_selected = False   # seleção por duplo/triplo clique ativa

        # Timer para distinguir single/double/triple click
        self._click_timer = QTimer()
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(self.CLICK_INTERVAL)
        self._click_timer.timeout.connect(self._commit_click)

        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    # ------------------------------------------------------------------ Qt

    def boundingRect(self) -> QRectF:
        return self._rect

    def paint(self, painter: QPainter, option, widget=None):
        for i in self._selected:
            painter.fillRect(self._words[i].rect, QColor(41, 128, 185, 90))

    # ------------------------------------------------------------------ Hover

    def _word_at(self, pos: QPointF) -> int | None:
        for i, w in enumerate(self._words):
            if w.rect.contains(pos):
                return i
        return None

    def hoverMoveEvent(self, event):
        on_word = self._word_at(event.pos()) is not None
        if on_word != self._on_text:
            self._on_text = on_word
            self.setCursor(Qt.CursorShape.IBeamCursor if on_word
                           else Qt.CursorShape.ArrowCursor)

    def hoverLeaveEvent(self, event):
        self._on_text = False
        self.setCursor(Qt.CursorShape.ArrowCursor)

    # ------------------------------------------------------------------ Mouse

    def mousePressEvent(self, event):
        self._last_pos = event.pos()
        self._click_count += 1

        if self._click_count == 1:
            self._multi_selected = False
            self._drag_start = event.pos()
            self._selected.clear()
            self._drag_rect  = QRectF()
            self._click_timer.start()
        elif self._click_count == 2:
            self._click_timer.stop()
            self._select_word(event.pos())
            self._multi_selected = True
            self._emit_selection()
            self._click_timer.start()   # aguarda possível triplo clique
        elif self._click_count >= 3:
            self._click_timer.stop()
            self._select_line(event.pos())
            self._multi_selected = True
            self._click_count = 0
            self._emit_selection()

        self.update()

    def mouseMoveEvent(self, event):
        # Drag só funciona no clique simples (antes do timer disparar)
        if self._drag_start is None or self._click_count != 1:
            return
        self._drag_rect = QRectF(self._drag_start, event.pos()).normalized()
        self._selected  = {
            i for i, w in enumerate(self._words)
            if self._drag_rect.intersects(w.rect)
        }
        self.update()

    def mouseReleaseEvent(self, event):
        if self._click_count == 1 and not self._drag_rect.isNull():
            # Finalizou drag — emite imediatamente
            self._click_timer.stop()
            self._click_count = 0
            self._drag_start  = None
            self._drag_rect   = QRectF()
            self._emit_selection()
        else:
            self._drag_start = None
            self._drag_rect  = QRectF()

    # ------------------------------------------------------------------ Click handlers

    def _commit_click(self):
        """Timer expirou — se foi clique simples sem drag, limpa seleção."""
        self._click_count = 0
        if not self._multi_selected:
            self._selected.clear()
            self.update()
        self._multi_selected = False

    def _select_word(self, pos: QPointF):
        """Seleciona a palavra sob o cursor."""
        self._selected.clear()
        idx = self._word_at(pos)
        if idx is not None:
            self._selected.add(idx)

    def _select_line(self, pos: QPointF):
        """Seleciona todas as palavras na mesma linha da palavra clicada."""
        self._selected.clear()
        idx = self._word_at(pos)
        if idx is None:
            return
        # Usa o centro Y da palavra como referência de linha
        ref_y  = self._words[idx].rect.center().y()
        line_h = self._words[idx].rect.height()
        tolerance = line_h * 0.6   # palavras na mesma linha variam um pouco

        self._selected = {
            i for i, w in enumerate(self._words)
            if abs(w.rect.center().y() - ref_y) <= tolerance
        }

    # ------------------------------------------------------------------ Emit

    def _emit_selection(self):
        if not self._selected:
            return
        ordered = sorted(self._selected,
                         key=lambda i: (self._words[i].rect.y(),
                                        self._words[i].rect.x()))
        text = " ".join(self._words[i].text for i in ordered)
        self._signals.text_selected.emit(text, self._page_index)

    def clear_selection(self):
        self._selected.clear()
        self.update()

    def select_by_rect(self, rect):
        """Seleciona palavras que intersectam rect (coords locais do item)."""
        self._selected = {
            i for i, w in enumerate(self._words)
            if rect.intersects(w.rect)
        }
        self.update()

    def get_selected_text(self) -> str:
        """Retorna texto das palavras selecionadas em ordem."""
        if not self._selected:
            return ""
        ordered = sorted(self._selected,
                         key=lambda i: (self._words[i].rect.y(),
                                        self._words[i].rect.x()))
        return " ".join(self._words[i].text for i in ordered)