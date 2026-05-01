from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject
from PySide6.QtGui import QColor, QPainter


class TextLayerSignals(QObject):
    text_selected     = Signal(str, int)   # text, page_index
    selection_cleared = Signal()
    highlight_clicked = Signal(int, int)   # highlight_id, page_index


class WordRect:
    __slots__ = ("text", "rect")
    def __init__(self, text: str, rect: QRectF):
        self.text = text
        self.rect = rect


class TextLayer(QGraphicsItem):
    """
    Camada de seleção de texto:
    - Clique + drag → seleção por ordem de leitura (âncora → foco)
    - Cursor IBeam apenas sobre palavras
    - Highlights persistentes renderizados em semi-transparente
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
        self._has_dragged = False
        self._on_text    = False
        self._highlights = []

        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    # ------------------------------------------------------------------ Qt

    def boundingRect(self) -> QRectF:
        return self._rect

    def paint(self, painter: QPainter, option, widget=None):
        # Highlights persistentes
        for h in self._highlights:
            c = QColor(h["color"])
            c.setAlpha(130)
            for r in h["rects"]:
                painter.fillRect(QRectF(r[0], r[1], r[2], r[3]), c)
        # Seleção atual
        sel_color = QColor(50, 150, 255, 140)
        for i in self._selected:
            painter.fillRect(self._words[i].rect, sel_color)

    # ------------------------------------------------------------------ Highlights

    def set_highlights(self, highlights: list):
        """highlights: list of {id, rects: [[x,y,w,h]], color} em coords locais."""
        self._highlights = highlights
        self.update()

    def highlight_id_at(self, pos: QPointF) -> int:
        """Retorna o id do highlight sob pos, ou -1 se não houver."""
        for h in self._highlights:
            for r in h["rects"]:
                if QRectF(r[0], r[1], r[2], r[3]).contains(pos):
                    return h.get("id", -1)
        return -1

    def get_selected_rects(self) -> list:
        """Retorna [[x, y, w, h]] das palavras selecionadas em coords locais."""
        return [
            [w.rect.x(), w.rect.y(), w.rect.width(), w.rect.height()]
            for i, w in enumerate(self._words) if i in self._selected
        ]

    def get_scene_bounding_rect(self) -> QRectF | None:
        """Bounding rect da seleção atual em coords de cena."""
        if not self._selected:
            return None
        x0 = min(self._words[i].rect.left()   for i in self._selected)
        y0 = min(self._words[i].rect.top()    for i in self._selected)
        x1 = max(self._words[i].rect.right()  for i in self._selected)
        y1 = max(self._words[i].rect.bottom() for i in self._selected)
        p = self.pos()
        return QRectF(x0 + p.x(), y0 + p.y(), x1 - x0, y1 - y0)

    def get_highlight_scene_rect(self, highlight_id: int) -> QRectF | None:
        """Bounding rect de um highlight específico em coords de cena."""
        for h in self._highlights:
            if h.get("id") == highlight_id:
                rects = h["rects"]
                if not rects:
                    return None
                x0 = min(r[0]      for r in rects)
                y0 = min(r[1]      for r in rects)
                x1 = max(r[0]+r[2] for r in rects)
                y1 = max(r[1]+r[3] for r in rects)
                p = self.pos()
                return QRectF(x0 + p.x(), y0 + p.y(), x1 - x0, y1 - y0)
        return None

    # ------------------------------------------------------------------ Ordem de leitura

    def _sorted_lines(self) -> list[list[int]]:
        """
        Agrupa palavras em linhas por proximidade de Y.
        Retorna lista de listas de índices, ordenadas top→bottom, left→right.
        """
        if not self._words:
            return []

        by_y = sorted(range(len(self._words)),
                      key=lambda i: self._words[i].rect.center().y())

        lines: list[list[int]] = []
        current: list[int] = []
        ref_y = ref_h = None

        for idx in by_y:
            cy = self._words[idx].rect.center().y()
            h  = self._words[idx].rect.height()
            if ref_y is None:
                ref_y, ref_h = cy, h
                current.append(idx)
            elif abs(cy - ref_y) <= max(ref_h, h) * 0.5:
                current.append(idx)
                ref_y = (ref_y + cy) / 2
            else:
                lines.append(sorted(current,
                                    key=lambda i: self._words[i].rect.x()))
                current = [idx]
                ref_y, ref_h = cy, h

        if current:
            lines.append(sorted(current,
                                 key=lambda i: self._words[i].rect.x()))
        return lines

    def _snap_to_word(self, pos: QPointF,
                      lines: list[list[int]]) -> int | None:
        """
        Encontra o índice de palavra mais representativo para a posição dada.
        - Se sobre uma palavra: essa palavra
        - Se antes/depois dos limites da linha: primeira/última palavra da linha
        - Usa a linha verticalmente mais próxima
        """
        if not lines:
            return None

        # Linha verticalmente mais próxima
        best_line: list[int] = []
        best_ydist = float("inf")
        for line in lines:
            mid_y = sum(self._words[i].rect.center().y() for i in line) / len(line)
            d = abs(mid_y - pos.y())
            if d < best_ydist:
                best_ydist = d
                best_line  = line

        # Acerto exato
        for i in best_line:
            if self._words[i].rect.contains(pos):
                return i

        leftmost  = best_line[0]
        rightmost = best_line[-1]

        if pos.x() <= self._words[leftmost].rect.left():
            return leftmost
        if pos.x() >= self._words[rightmost].rect.right():
            return rightmost

        # Palavra cujo centro X é mais próximo
        best_w     = leftmost
        best_xdist = float("inf")
        for i in best_line:
            d = abs(self._words[i].rect.center().x() - pos.x())
            if d < best_xdist:
                best_xdist = d
                best_w     = i
        return best_w

    def _select_range(self, start_pos: QPointF, end_pos: QPointF):
        """
        Seleciona todas as palavras entre start_pos e end_pos na ordem de
        leitura (linha por linha, da esquerda para direita).
        Isso garante que linhas inteiras intermediárias sejam incluídas.
        """
        lines = self._sorted_lines()
        if not lines:
            return

        anchor_idx = self._snap_to_word(start_pos, lines)
        focus_idx  = self._snap_to_word(end_pos,   lines)
        if anchor_idx is None or focus_idx is None:
            return

        flat = [i for line in lines for i in line]
        try:
            a = flat.index(anchor_idx)
            f = flat.index(focus_idx)
        except ValueError:
            return

        lo, hi = min(a, f), max(a, f)
        self._selected = set(flat[lo : hi + 1])

    # ------------------------------------------------------------------ Métodos para view contínua

    def select_from_anchor(self, anchor_scene: QPointF):
        """Seleciona da âncora até o fim da página (primeira página do drag)."""
        local = QPointF(anchor_scene.x() - self.pos().x(),
                        anchor_scene.y() - self.pos().y())
        end   = QPointF(self._rect.right(), self._rect.bottom())
        self._select_range(local, end)
        self.update()

    def select_to_focus(self, focus_scene: QPointF):
        """Seleciona do início da página até o foco (última página do drag)."""
        start = QPointF(0.0, 0.0)
        local = QPointF(focus_scene.x() - self.pos().x(),
                        focus_scene.y() - self.pos().y())
        self._select_range(start, local)
        self.update()

    def select_range_scene(self, anchor_scene: QPointF, focus_scene: QPointF):
        """Seleção por range em coords de cena (página única no drag contínuo)."""
        a = QPointF(anchor_scene.x() - self.pos().x(),
                    anchor_scene.y() - self.pos().y())
        f = QPointF(focus_scene.x()  - self.pos().x(),
                    focus_scene.y()  - self.pos().y())
        self._select_range(a, f)
        self.update()

    def select_all(self):
        """Seleciona todas as palavras da página (páginas intermediárias do drag)."""
        self._selected = set(range(len(self._words)))
        self.update()

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
        hid = self.highlight_id_at(event.pos())
        if hid >= 0:
            self._signals.highlight_clicked.emit(hid, self._page_index)
            return

        self._drag_start  = event.pos()
        self._has_dragged = False
        self._selected.clear()
        self.update()

    def mouseMoveEvent(self, event):
        if self._drag_start is None:
            return
        if (event.pos() - self._drag_start).manhattanLength() > 3:
            self._has_dragged = True
        self._select_range(self._drag_start, event.pos())
        self.update()

    def mouseReleaseEvent(self, event):
        if self._has_dragged:
            self._emit_selection()
        else:
            self._selected.clear()
            self._signals.selection_cleared.emit()
            self.update()
        self._drag_start  = None
        self._has_dragged = False

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
        had = bool(self._selected)
        self._selected.clear()
        if had:
            self._signals.selection_cleared.emit()
        self.update()

    def get_selected_text(self) -> str:
        if not self._selected:
            return ""
        ordered = sorted(self._selected,
                         key=lambda i: (self._words[i].rect.y(),
                                        self._words[i].rect.x()))
        return " ".join(self._words[i].text for i in ordered)

    # mantido para compatibilidade (não mais usado no drag)
    def select_by_rect(self, rect: QRectF):
        self._selected = {
            i for i, w in enumerate(self._words)
            if rect.intersects(w.rect)
        }
        self.update()
