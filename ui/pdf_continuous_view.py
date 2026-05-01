import fitz
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene,
                                QGraphicsPixmapItem, QGraphicsRectItem)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer, QRectF, QPointF
from PySide6.QtGui import QPixmap, QImage, QColor, QPen, QBrush, QWheelEvent
from ui.text_layer import TextLayer, TextLayerSignals, WordRect

PAGE_GAP    = 16
PRELOAD_PX  = 900
MIN_QUALITY = 2.0
HIRES_DELAY = 220


class PageRenderer(QObject):
    """Renderiza página no zoom atual — qualidade sempre nativa."""
    done = Signal(int, QPixmap, float, list)  # index, pixmap, render_zoom, words

    def __init__(self, doc, index: int, render_zoom: float):
        super().__init__()
        self._doc         = doc
        self._index       = index
        self._render_zoom = render_zoom

    def run(self):
        try:
            page = self._doc[self._index]
            mat  = fitz.Matrix(self._render_zoom, self._render_zoom)
            pix  = page.get_pixmap(matrix=mat, alpha=False)
            img  = QImage(pix.samples, pix.width, pix.height,
                          pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img.copy())

            words = []
            for w in page.get_text("words"):
                x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
                words.append(WordRect(text, QRectF(x0, y0, x1-x0, y1-y0)))

            self.done.emit(self._index, pixmap, self._render_zoom, words)
        except Exception:
            pass


class PDFContinuousView(QGraphicsView):
    """
    Visualização contínua com qualidade de renderização adaptativa.
    - Pixmaps sempre renderizados em max(MIN_QUALITY, zoom_atual)
    - Zoom visual instantâneo via view.scale() (GPU)
    - Debounce: re-renderiza páginas visíveis no novo zoom após parar
    - Zero upscaling: qualidade sempre nativa ao nível de zoom
    - Suporte a marca texto persistente e duplo/triplo clique
    """

    page_changed = Signal(int, int)
    zoom_changed = Signal(float)

    def __init__(self, doc, pdf_path: str = "", parent=None):
        super().__init__(parent)
        self._doc          = doc
        self._pdf_path     = pdf_path
        self._page_tops    = []
        self._page_heights = []
        self._page_widths  = []
        self._placeholders = {}
        self._pixmap_items = {}
        self._render_zooms = {}
        self._text_layers  = {}
        self._loading      = set()
        self._threads      = {}
        self._current_page = 0
        self.text_signals  = TextLayerSignals()

        # Seleção por drag
        self._drag_selecting   = False
        self._drag_start_scene = None
        self._drag_start_vp    = None

        self._hires_timer = QTimer(self)
        self._hires_timer.setSingleShot(True)
        self._hires_timer.timeout.connect(self._hires_reload)

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
        self._render_zooms.clear()
        self._text_layers.clear()
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

    def _render_zoom_needed(self) -> float:
        return max(MIN_QUALITY, self.transform().m11())

    def _needs_rerender(self, index: int) -> bool:
        if index not in self._render_zooms:
            return True
        return self._render_zoom_needed() > self._render_zooms[index] + 0.05

    def _lazy_load(self):
        if not self._page_tops:
            return
        top_y, bot_y = self._visible_range()
        for i in range(len(self._doc)):
            in_view = (self._page_tops[i] + self._page_heights[i] >= top_y and
                       self._page_tops[i] <= bot_y)
            if in_view and self._needs_rerender(i) and i not in self._loading:
                self._render_page(i)

    def _render_page(self, index: int):
        self._loading.add(index)
        render_zoom = self._render_zoom_needed()

        thread   = QThread(self)
        renderer = PageRenderer(self._doc, index, render_zoom)
        renderer.moveToThread(thread)
        renderer.done.connect(self._on_render_done)
        thread.started.connect(renderer.run)
        self._threads[index] = (thread, renderer)
        thread.start()

    def _on_render_done(self, index: int, pixmap: QPixmap,
                         render_zoom: float, words: list):
        self._loading.discard(index)
        if index in self._threads:
            thread, _ = self._threads.pop(index)
            thread.quit()
        if index >= len(self._page_widths):
            return

        existing = self._render_zooms.get(index, 0)
        if render_zoom < existing - 0.05:
            return

        scene_w  = self._scene.sceneRect().width()
        page_w   = self._page_widths[index]
        page_top = self._page_tops[index]
        s = 1.0 / render_zoom
        x = (scene_w - page_w) / 2

        self._render_zooms[index] = render_zoom

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

        # Text layer criado apenas uma vez por página (coords de documento)
        if index not in self._text_layers:
            tl = TextLayer(QRectF(0, 0, page_w, self._page_heights[index]),
                           words, index, self.text_signals)
            tl.setPos(x, page_top)
            tl.set_highlights(self._load_highlights_for_layer(index))
            self._scene.addItem(tl)
            self._text_layers[index] = tl

    # ------------------------------------------------------------------ Highlights

    def _load_highlights_for_layer(self, page_index: int) -> list:
        """Carrega highlights em coords de documento (mesmas do TextLayer)."""
        if not self._pdf_path:
            return []
        from core.highlights import get_page_highlights
        return [{"id": h["id"], "rects": h["rects"], "color": h["color"]}
                for h in get_page_highlights(self._pdf_path, page_index)]

    def refresh_highlights(self, page_index: int):
        if page_index in self._text_layers:
            self._text_layers[page_index].set_highlights(
                self._load_highlights_for_layer(page_index))

    def get_selection_viewport_rect(self):
        """Une os bounding rects de todas as seleções e retorna em coords do viewport."""
        from PySide6.QtCore import QRect, QPoint
        scene_rects = [tl.get_scene_bounding_rect()
                       for tl in self._text_layers.values()]
        scene_rects = [r for r in scene_rects if r is not None]
        if not scene_rects:
            return None
        x0 = min(r.left()   for r in scene_rects)
        y0 = min(r.top()    for r in scene_rects)
        x1 = max(r.right()  for r in scene_rects)
        y1 = max(r.bottom() for r in scene_rects)
        from PySide6.QtCore import QPointF
        return QRect(self.mapFromScene(QPointF(x0, y0)),
                     self.mapFromScene(QPointF(x1, y1))).normalized()

    def get_highlight_viewport_rect(self, highlight_id: int, page_index: int):
        """Retorna QRect de um highlight em coords do viewport, ou None."""
        tl = self._text_layers.get(page_index)
        if not tl:
            return None
        sr = tl.get_highlight_scene_rect(highlight_id)
        if sr is None:
            return None
        from PySide6.QtCore import QRect
        return QRect(self.mapFromScene(sr.topLeft()),
                     self.mapFromScene(sr.bottomRight())).normalized()

    def get_selection_info(self) -> dict:
        """Retorna {page_index: [[x,y,w,h], ...]} em coords de documento."""
        result = {}
        for idx, tl in self._text_layers.items():
            rects = tl.get_selected_rects()
            if rects:
                result[idx] = rects
        return result

    def clear_selection(self):
        for tl in self._text_layers.values():
            tl.clear_selection()

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
        self._hires_timer.start(HIRES_DELAY)

    def _hires_reload(self):
        top_y, bot_y = self._visible_range()
        for i in range(len(self._doc)):
            in_view = (self._page_tops[i] + self._page_heights[i] >= top_y and
                       self._page_tops[i] <= bot_y)
            if in_view and self._needs_rerender(i) and i not in self._loading:
                self._render_page(i)

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

    # ------------------------------------------------------------------ Helpers

    def _text_layer_at(self, scene_pos: QPointF) -> TextLayer | None:
        for tl in self._text_layers.values():
            if tl.boundingRect().translated(tl.pos()).contains(scene_pos):
                return tl
        return None

    # ------------------------------------------------------------------ Eventos de mouse

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            tl_hit    = self._text_layer_at(scene_pos)

            if tl_hit is not None:
                local = QPointF(scene_pos.x() - tl_hit.pos().x(),
                                scene_pos.y() - tl_hit.pos().y())
                hid = tl_hit.highlight_id_at(local)
                if hid >= 0:
                    page_idx = next(
                        (i for i, tl in self._text_layers.items() if tl is tl_hit), 0)
                    self.text_signals.highlight_clicked.emit(hid, page_idx)
                    return

                for tl in self._text_layers.values():
                    tl.clear_selection()
                self._drag_start_scene = scene_pos
                self._drag_start_vp    = event.pos()
                self._drag_selecting   = False
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self._drag_start_scene is not None
                and not self._drag_selecting
                and self._drag_start_vp is not None
                and (event.pos() - self._drag_start_vp).manhattanLength() > 6):
            self._drag_selecting = True

        if self._drag_selecting and self._drag_start_scene is not None:
            scene_pos = self.mapToScene(event.pos())

            if self._drag_start_scene.y() <= scene_pos.y():
                anchor_scene = self._drag_start_scene
                focus_scene  = scene_pos
            else:
                anchor_scene = scene_pos
                focus_scene  = self._drag_start_scene

            for tl in self._text_layers.values():
                tl_top    = tl.pos().y()
                tl_bottom = tl_top + tl.boundingRect().height()

                anchor_in = tl_top <= anchor_scene.y() <= tl_bottom
                focus_in  = tl_top <= focus_scene.y()  <= tl_bottom
                above     = tl_bottom < anchor_scene.y()
                below     = tl_top    > focus_scene.y()

                if above or below:
                    tl.clear_selection()
                elif anchor_in and focus_in:
                    tl.select_range_scene(anchor_scene, focus_scene)
                elif anchor_in:
                    tl.select_from_anchor(anchor_scene)
                elif focus_in:
                    tl.select_to_focus(focus_scene)
                else:
                    tl.select_all()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_selecting:
                texts = []
                for i in sorted(self._text_layers):
                    txt = self._text_layers[i].get_selected_text()
                    if txt:
                        texts.append(txt)
                if texts:
                    self.text_signals.text_selected.emit(" ".join(texts), 0)
            self._drag_selecting   = False
            self._drag_start_scene = None
            self._drag_start_vp    = None
            return

        super().mouseReleaseEvent(event)

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
            self._hires_timer.start(HIRES_DELAY)
            return

        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            delta = event.angleDelta().y()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta)
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
