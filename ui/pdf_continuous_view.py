import fitz
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem
from PySide6.QtCore import Qt, Signal, QThread, QObject, QRectF, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor, QPen, QBrush, QWheelEvent

PAGE_GAP    = 16   # px entre páginas
PRELOAD_PX  = 1200 # px além da viewport para pré-carregar
HIRES_DELAY = 300  # ms de debounce após zoom


class PageRenderer(QObject):
    """Renderiza uma página em thread separada."""
    done = Signal(int, QPixmap, float)

    def __init__(self, doc, index: int, zoom: float):
        super().__init__()
        self._doc   = doc
        self._index = index
        self._zoom  = zoom

    def run(self):
        try:
            page = self._doc[self._index]
            mat  = fitz.Matrix(self._zoom, self._zoom)
            pix  = page.get_pixmap(matrix=mat, alpha=False)
            img  = QImage(pix.samples, pix.width, pix.height,
                          pix.stride, QImage.Format.Format_RGB888)
            self.done.emit(self._index, QPixmap.fromImage(img.copy()), self._zoom)
        except Exception:
            pass


class PDFContinuousView(QGraphicsView):
    """
    Visualização contínua — todas as páginas empilhadas verticalmente.
    - Lazy loading: renderiza apenas páginas próximas da viewport
    - Zoom suave: preview instantâneo + hi-res com debounce
    - Ctrl+Scroll para zoom
    """

    page_changed = Signal(int, int)   # current (1-based), total
    zoom_changed = Signal(float)

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self._doc          = doc
        self._zoom         = 1.5
        self._page_tops    = []    # y de topo de cada página na scene
        self._page_heights = []    # altura de cada página no zoom atual
        self._page_widths  = []    # largura de cada página no zoom atual
        self._placeholders = {}    # index -> QGraphicsRectItem (fundo cinza)
        self._pixmap_items = {}    # index -> QGraphicsPixmapItem
        self._source_pixmaps = {}  # index -> QPixmap hi-res
        self._stale        = set() # páginas com zoom desatualizado
        self._loading      = set() # renderizações em curso
        self._threads      = {}    # index -> (QThread, PageRenderer)
        self._current_page = 0
        self._hires_timer  = QTimer(self)
        self._hires_timer.setSingleShot(True)
        self._hires_timer.timeout.connect(self._do_hires_reload)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(self.renderHints().SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.setStyleSheet("border: none; background: #181818;")
        self.setBackgroundBrush(QColor("#181818"))

        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self._build_layout()
        QTimer.singleShot(50, self._lazy_load)

    # ------------------------------------------------------------------ Layout

    def _build_layout(self):
        """Calcula posições e cria placeholders para todas as páginas."""
        self._scene.clear()
        self._placeholders.clear()
        self._pixmap_items.clear()
        self._page_tops.clear()
        self._page_heights.clear()
        self._page_widths.clear()

        y = PAGE_GAP
        for i in range(len(self._doc)):
            page = self._doc[i]
            w    = int(page.rect.width  * self._zoom)
            h    = int(page.rect.height * self._zoom)
            self._page_tops.append(y)
            self._page_heights.append(h)
            self._page_widths.append(w)

            # Placeholder cinza escuro
            rect = QGraphicsRectItem(0, 0, w, h)
            rect.setPos(0, y)
            rect.setBrush(QBrush(QColor("#2a2a2a")))
            rect.setPen(QPen(Qt.PenStyle.NoPen))
            self._scene.addItem(rect)
            self._placeholders[i] = rect

            y += h + PAGE_GAP

        self._update_scene_rect()

    def _update_scene_rect(self):
        max_w = max(self._page_widths) if self._page_widths else 800
        total_h = (self._page_tops[-1] + self._page_heights[-1] + PAGE_GAP
                   if self._page_tops else 800)
        vp_w = self.viewport().width()
        self._scene.setSceneRect(0, 0, max(max_w, vp_w), total_h)
        self._center_pages()

    def _center_pages(self):
        """Centraliza os placeholders e pixmaps horizontalmente."""
        vp_w = self.viewport().width()
        for i, w in enumerate(self._page_widths):
            x = max(0, (vp_w - w) // 2)
            if i in self._placeholders:
                self._placeholders[i].setPos(x, self._page_tops[i])
            if i in self._pixmap_items:
                self._pixmap_items[i].setPos(x, self._page_tops[i])

    # ------------------------------------------------------------------ Lazy load

    def _visible_range(self):
        """Retorna (top_y, bottom_y) da área visível + margem."""
        vbar    = self.verticalScrollBar()
        vp_h    = self.viewport().height()
        top_y   = vbar.value() - PRELOAD_PX
        bot_y   = vbar.value() + vp_h + PRELOAD_PX
        return top_y, bot_y

    def _lazy_load(self):
        top_y, bot_y = self._visible_range()
        for i in range(len(self._doc)):
            in_view = (self._page_tops[i] + self._page_heights[i] >= top_y and
                       self._page_tops[i] <= bot_y)
            needs   = i not in self._source_pixmaps or i in self._stale
            if in_view and needs and i not in self._loading:
                self._render_page(i)

    def _render_page(self, index: int):
        self._loading.add(index)
        zoom = self._zoom

        thread   = QThread(self)
        renderer = PageRenderer(self._doc, index, zoom)
        renderer.moveToThread(thread)
        renderer.done.connect(self._on_render_done)
        thread.started.connect(renderer.run)
        self._threads[index] = (thread, renderer)
        thread.start()

    def _on_render_done(self, index: int, pixmap: QPixmap, zoom_at_render: float):
        self._loading.discard(index)
        if index in self._threads:
            thread, _ = self._threads.pop(index)
            thread.quit()

        if zoom_at_render != self._zoom:
            return  # zoom mudou, descarta

        self._source_pixmaps[index] = pixmap
        self._stale.discard(index)
        self._place_pixmap(index, pixmap)

    def _place_pixmap(self, index: int, pixmap: QPixmap):
        vp_w = self.viewport().width()
        x    = max(0, (vp_w - pixmap.width()) // 2)
        y    = self._page_tops[index]

        if index in self._pixmap_items:
            self._pixmap_items[index].setPixmap(pixmap)
            self._pixmap_items[index].setPos(x, y)
        else:
            item = QGraphicsPixmapItem(pixmap)
            item.setPos(x, y)
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            self._scene.addItem(item)
            self._pixmap_items[index] = item

    # ------------------------------------------------------------------ Zoom suave

    def _apply_preview(self):
        """Resize instantâneo (NEAREST) nas páginas visíveis — sem limpar a cena."""
        top_y, bot_y = self._visible_range()
        for i, src in self._source_pixmaps.items():
            if not (self._page_tops[i] + self._page_heights[i] >= top_y and
                    self._page_tops[i] <= bot_y):
                continue
            scaled = src.scaled(
                self._page_widths[i], self._page_heights[i],
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            self._place_pixmap(i, scaled)

    def _do_hires_reload(self):
        """Marca como stale e relança lazy load — preview permanece até hi-res chegar."""
        self._stale.update(range(len(self._doc)))
        self._loading.clear()
        self._lazy_load()

    # ------------------------------------------------------------------ Navegação

    def go_to_page(self, index: int):
        if 0 <= index < len(self._doc):
            self.verticalScrollBar().setValue(int(self._page_tops[index]))
            self._current_page = index
            self._lazy_load()

    def next_page(self):
        self.go_to_page(self._current_page + 1)

    def prev_page(self):
        self.go_to_page(self._current_page - 1)

    @property
    def current_page(self) -> int:
        return self._current_page + 1

    @property
    def total_pages(self) -> int:
        return len(self._doc)

    # ------------------------------------------------------------------ Zoom

    def set_zoom(self, zoom: float):
        zoom = max(0.25, min(zoom, 5.0))
        if zoom == self._zoom:
            return
        current = self._current_page
        self._zoom = zoom

        # Recalcula dimensões
        for i in range(len(self._doc)):
            page = self._doc[i]
            self._page_widths[i]  = int(page.rect.width  * zoom)
            self._page_heights[i] = int(page.rect.height * zoom)

        # Recalcula tops
        y = PAGE_GAP
        for i in range(len(self._doc)):
            self._page_tops[i] = y
            y += self._page_heights[i] + PAGE_GAP

        # Reposiciona placeholders
        vp_w = self.viewport().width()
        for i in range(len(self._doc)):
            x = max(0, (vp_w - self._page_widths[i]) // 2)
            if i in self._placeholders:
                ph = self._placeholders[i]
                ph.setRect(0, 0, self._page_widths[i], self._page_heights[i])
                ph.setPos(x, self._page_tops[i])

        self._update_scene_rect()

        # Preview instantâneo
        self._apply_preview()

        # Volta para a página atual
        QTimer.singleShot(10, lambda: self.go_to_page(current))

        # Debounce hi-res
        self._hires_timer.start(HIRES_DELAY)
        self.zoom_changed.emit(zoom)

    def zoom_in(self):    self.set_zoom(self._zoom + 0.25)
    def zoom_out(self):   self.set_zoom(self._zoom - 0.25)
    def zoom_reset(self): self.set_zoom(1.5)

    @property
    def zoom(self) -> float:
        return self._zoom

    # ------------------------------------------------------------------ Eventos

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            self.set_zoom(self._zoom + (0.15 if delta > 0 else -0.15))
            return
        super().wheelEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scene_rect()

    def _on_scroll(self):
        self._lazy_load()
        self._update_current_page()

    def _update_current_page(self):
        vbar  = self.verticalScrollBar()
        mid_y = vbar.value() + self.viewport().height() // 2
        for i in range(len(self._doc) - 1, -1, -1):
            if self._page_tops[i] <= mid_y:
                if i != self._current_page:
                    self._current_page = i
                    self.page_changed.emit(i + 1, len(self._doc))
                break