import fitz
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene,
                                QGraphicsPixmapItem, QGraphicsRectItem)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer, QRectF
from PySide6.QtGui import QPixmap, QImage, QColor, QPen, QBrush, QWheelEvent
from ui.text_layer import TextLayer, TextLayerSignals, WordRect

PAGE_GAP    = 16
PRELOAD_PX  = 900
RENDER_DPI  = 2.0


class PageRenderer(QObject):
    """Renderiza página E extrai palavras na mesma thread."""
    done = Signal(int, QPixmap, list)  # index, pixmap, words

    def __init__(self, doc, index: int):
        super().__init__()
        self._doc   = doc
        self._index = index

    def run(self):
        try:
            page = self._doc[self._index]
            mat  = fitz.Matrix(RENDER_DPI, RENDER_DPI)
            pix  = page.get_pixmap(matrix=mat, alpha=False)
            img  = QImage(pix.samples, pix.width, pix.height,
                          pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img.copy())

            # Palavras em PDF points (scale=1.0) — scene está em PDF points
            words = []
            for w in page.get_text("words"):
                x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
                words.append(WordRect(text, QRectF(x0, y0, x1-x0, y1-y0)))

            self.done.emit(self._index, pixmap, words)
        except Exception:
            pass


class PDFContinuousView(QGraphicsView):
    """Visualização contínua com seleção de texto."""

    page_changed = Signal(int, int)
    zoom_changed = Signal(float)

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self._doc          = doc
        self._page_tops    = []
        self._page_heights = []
        self._page_widths  = []
        self._placeholders = {}
        self._pixmap_items = {}
        self._text_layers  = {}
        self._loading      = set()
        self._threads      = {}
        self._current_page = 0
        self.text_signals  = TextLayerSignals()

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(self.renderHints().SmoothPixmapTransform, True)
        self.setRenderHint(self.renderHints().Antialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.setStyleSheet("border:none; background:#181818;")
        self.setBackgroundBrush(QColor("#181818"))

        self.scale(1.5, 1.5)

        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self._build_layout()
        QTimer.singleShot(60, self._lazy_load)

    # ------------------------------------------------------------------ Layout

    def _build_layout(self):
        self._scene.clear()
        self._placeholders.clear()
        self._pixmap_items.clear()
        self._text_layers.clear()   # ← crítico: limpa antes de scene.clear()
        self._loading.clear()
        self._threads.clear()
        self._page_tops.clear()
        self._page_heights.clear()
        self._page_widths.clear()

        y = PAGE_GAP
        for i in range(len(self._doc)):
            page = self._doc[i]
            w    = page.rect.width
            h    = page.rect.height
            self._page_tops.append(y)
            self._page_heights.append(h)
            self._page_widths.append(w)

            rect = QGraphicsRectItem(0, 0, w, h)
            rect.setBrush(QBrush(QColor("#2a2a2a")))
            rect.setPen(QPen(Qt.PenStyle.NoPen))
            self._scene.addItem(rect)
            self._placeholders[i] = rect
            y += h + PAGE_GAP

        self._update_scene_rect()

    def _update_scene_rect(self):
        if not self._page_tops:
            return
        max_w   = max(self._page_widths)
        total_h = self._page_tops[-1] + self._page_heights[-1] + PAGE_GAP
        zoom    = self.transform().m11()
        vp_w    = self.viewport().width() / zoom if zoom > 0 else max_w
        scene_w = max(max_w, vp_w)
        self._scene.setSceneRect(0, 0, scene_w, total_h)
        self._center_items()

    def _center_items(self):
        scene_w = self._scene.sceneRect().width()
        for i in range(len(self._doc)):
            x = (scene_w - self._page_widths[i]) / 2
            if i in self._placeholders:
                self._placeholders[i].setPos(x, self._page_tops[i])
            if i in self._pixmap_items:
                self._pixmap_items[i].setPos(x, self._page_tops[i])
            if i in self._text_layers:
                self._text_layers[i].setPos(x, self._page_tops[i])

    # ------------------------------------------------------------------ Lazy load

    def _visible_range(self):
        zoom  = self.transform().m11()
        vbar  = self.verticalScrollBar()
        vp_h  = self.viewport().height()
        top_y = vbar.value() / zoom - PRELOAD_PX
        bot_y = (vbar.value() + vp_h) / zoom + PRELOAD_PX
        return top_y, bot_y

    def _lazy_load(self):
        if not self._page_tops:
            return
        top_y, bot_y = self._visible_range()
        for i in range(len(self._doc)):
            in_view = (self._page_tops[i] + self._page_heights[i] >= top_y and
                       self._page_tops[i] <= bot_y)
            if in_view and i not in self._pixmap_items and i not in self._loading:
                self._render_page(i)

    def _render_page(self, index: int):
        self._loading.add(index)
        thread   = QThread(self)
        renderer = PageRenderer(self._doc, index)
        renderer.moveToThread(thread)
        renderer.done.connect(self._on_render_done)
        thread.started.connect(renderer.run)
        self._threads[index] = (thread, renderer)
        thread.start()

    def _on_render_done(self, index: int, pixmap: QPixmap, words: list):
        self._loading.discard(index)
        if index in self._threads:
            thread, _ = self._threads.pop(index)
            thread.quit()
        if index >= len(self._page_widths):
            return

        scene_w  = self._scene.sceneRect().width()
        page_w   = self._page_widths[index]
        page_top = self._page_tops[index]
        s        = 1.0 / RENDER_DPI
        x        = (scene_w - page_w) / 2

        # Pixmap item
        if index in self._pixmap_items:
            self._pixmap_items[index].setPixmap(pixmap)
            self._pixmap_items[index].setScale(s)
            self._pixmap_items[index].setPos(x, page_top)
        else:
            item = QGraphicsPixmapItem(pixmap)
            item.setScale(s)
            item.setPos(x, page_top)
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            self._scene.addItem(item)
            self._pixmap_items[index] = item

        # Text layer — apenas uma vez por página
        if index not in self._text_layers:
            tl = TextLayer(QRectF(0, 0, page_w, self._page_heights[index]),
                           words, index, self.text_signals)
            tl.setPos(x, page_top)
            self._scene.addItem(tl)
            self._text_layers[index] = tl

    # ------------------------------------------------------------------ Zoom

    @property
    def zoom(self) -> float:
        return self.transform().m11()

    def set_zoom(self, target: float):
        target  = max(0.25, min(target, 5.0))
        current = self.transform().m11()
        if abs(target - current) < 0.01:
            return
        factor = target / current
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.scale(factor, factor)
        self._update_scene_rect()
        self.zoom_changed.emit(self.zoom)

    def zoom_in(self):    self.set_zoom(round(self.zoom + 0.25, 2))
    def zoom_out(self):   self.set_zoom(round(self.zoom - 0.25, 2))
    def zoom_reset(self): self.set_zoom(1.5)

    # ------------------------------------------------------------------ Navegação

    def go_to_page(self, index: int):
        if 0 <= index < len(self._doc):
            zoom    = self.transform().m11()
            scene_y = self._page_tops[index]
            self.verticalScrollBar().setValue(int(scene_y * zoom))
            self._current_page = index
            self._lazy_load()

    def next_page(self): self.go_to_page(self._current_page + 1)
    def prev_page(self): self.go_to_page(self._current_page - 1)

    @property
    def current_page(self) -> int: return self._current_page + 1
    @property
    def total_pages(self) -> int:  return len(self._doc)

    # ------------------------------------------------------------------ Eventos

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta  = event.angleDelta().y()
            factor = 1.15 if delta > 0 else 1 / 1.15
            new_zoom = self.zoom * factor
            if not (0.25 <= new_zoom <= 5.0):
                return
            self.setTransformationAnchor(
                QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            self.scale(factor, factor)
            self._update_scene_rect()
            self.zoom_changed.emit(self.zoom)
            return
        super().wheelEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._page_tops:
            self._update_scene_rect()

    def _on_scroll(self):
        self._lazy_load()
        self._update_current_page()

    def _update_current_page(self):
        zoom  = self.transform().m11()
        vbar  = self.verticalScrollBar()
        mid_y = (vbar.value() + self.viewport().height() / 2) / zoom
        for i in range(len(self._doc) - 1, -1, -1):
            if self._page_tops[i] <= mid_y:
                if i != self._current_page:
                    self._current_page = i
                    self.page_changed.emit(i + 1, len(self._doc))
                break