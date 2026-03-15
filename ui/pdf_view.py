import fitz
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtCore import Qt, Signal, QThread, QObject, QRectF, QTimer
from PySide6.QtGui import QPixmap, QImage, QTransform, QWheelEvent, QColor


class PageRenderer(QObject):
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


class PDFView(QGraphicsView):
    """
    Visualizador página única.
    Zoom suave: setTransform() instantâneo (GPU) + hi-res em background com debounce.
    """

    page_changed = Signal(int, int)
    zoom_changed = Signal(float)

    HIRES_DELAY = 250   # ms após último zoom para disparar hi-res

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self._doc          = doc
        self._page_index   = 0
        self._zoom         = 1.5
        self._base_zoom    = 1.5   # zoom em que o pixmap atual foi renderizado
        self._pixmap_item  = None
        self._render_thread = None
        self._renderer     = None
        self._hires_timer  = QTimer(self)
        self._hires_timer.setSingleShot(True)
        self._hires_timer.timeout.connect(self._render_hires)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(self.renderHints().SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("border:none; background:#181818;")
        self.setBackgroundBrush(QColor("#181818"))

        # Renderiza a primeira página em hi-res na base zoom
        self._render_hires()

    # ------------------------------------------------------------------ Render

    def _render_hires(self):
        """Renderiza o pixmap em hi-res na resolução exata do zoom atual."""
        if self._render_thread and self._render_thread.isRunning():
            self._render_thread.quit()
            self._render_thread.wait(100)

        zoom = self._zoom
        self._render_thread = QThread(self)
        self._renderer = PageRenderer(self._doc, self._page_index, zoom)
        self._renderer.moveToThread(self._render_thread)
        self._renderer.done.connect(self._on_hires_ready)
        self._render_thread.started.connect(self._renderer.run)
        self._render_thread.start()

    def _on_hires_ready(self, index: int, pixmap: QPixmap, zoom_at_render: float):
        if self._render_thread:
            self._render_thread.quit()

        # Descarta se página ou zoom mudou
        if index != self._page_index or zoom_at_render != self._zoom:
            return

        self._base_zoom = zoom_at_render

        # Reseta transform para 1:1 e coloca o pixmap em resolução nativa
        self.resetTransform()

        self._scene.clear()
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._pixmap_item.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation)
        self._scene.addItem(self._pixmap_item)
        self._scene.setSceneRect(QRectF(self._pixmap_item.boundingRect()))
        self.centerOn(self._pixmap_item)

        self.page_changed.emit(self._page_index + 1, len(self._doc))
        self.zoom_changed.emit(self._zoom)

    # ------------------------------------------------------------------ Zoom

    def set_zoom(self, zoom: float):
        zoom = max(0.25, min(zoom, 5.0))
        if zoom == self._zoom:
            return
        self._zoom = zoom

        # Passo 1: transform instantâneo via GPU — sem re-renderizar nada
        if self._pixmap_item and self._base_zoom > 0:
            scale = zoom / self._base_zoom
            self.setTransform(QTransform().scale(scale, scale))

        # Passo 2: debounce — re-renderiza hi-res só quando parar de dar zoom
        self._hires_timer.start(self.HIRES_DELAY)
        self.zoom_changed.emit(zoom)

    def zoom_in(self):    self.set_zoom(self._zoom + 0.25)
    def zoom_out(self):   self.set_zoom(self._zoom - 0.25)
    def zoom_reset(self): self.set_zoom(1.5)

    @property
    def zoom(self) -> float:
        return self._zoom

    # ------------------------------------------------------------------ Navegação

    def go_to(self, page_index: int):
        if 0 <= page_index < len(self._doc):
            self._page_index = page_index
            self.resetTransform()
            self._base_zoom = self._zoom
            self._render_hires()
            self.verticalScrollBar().setValue(0)

    def next_page(self): self.go_to(self._page_index + 1)
    def prev_page(self): self.go_to(self._page_index - 1)

    @property
    def current_page(self) -> int: return self._page_index + 1
    @property
    def total_pages(self) -> int:  return len(self._doc)

    # ------------------------------------------------------------------ Scroll contínuo

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            self.set_zoom(self._zoom + (0.15 if delta > 0 else -0.15))
            return

        delta = event.angleDelta().y()
        vbar  = self.verticalScrollBar()

        if delta < 0 and vbar.value() == vbar.maximum():
            if self._page_index < len(self._doc) - 1:
                self.go_to(self._page_index + 1)
                return

        if delta > 0 and vbar.value() == vbar.minimum():
            if self._page_index > 0:
                self.go_to(self._page_index - 1)
                vbar.setValue(vbar.maximum())
                return

        super().wheelEvent(event)