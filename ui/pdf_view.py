import fitz
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtCore import Qt, Signal, QThread, QObject, QRectF
from PySide6.QtGui import QPixmap, QImage, QTransform, QWheelEvent


class PageRenderer(QObject):
    """Renderiza uma página do PDF em thread separada."""
    done = Signal(int, QPixmap, float)   # page_index, pixmap, zoom_at_render

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
    Visualizador de PDF em modo página única.
    - Scroll nativo Qt
    - Ctrl+Scroll para zoom
    - Renderização em thread separada
    """

    page_changed = Signal(int, int)    # current (1-based), total
    zoom_changed = Signal(float)

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self._doc        = doc
        self._page_index = 0
        self._zoom       = 1.5
        self._pixmap_item = None
        self._render_thread = None
        self._renderer = None

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(self.renderHints().Antialiasing, True)
        self.setRenderHint(self.renderHints().SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)
        self.setStyleSheet("border: none; background: #181818;")

        self._render_page()

    # ------------------------------------------------------------------ Render

    def _render_page(self):
        """Dispara renderização em thread separada."""
        if self._render_thread and self._render_thread.isRunning():
            self._render_thread.quit()
            self._render_thread.wait(200)

        self._render_thread = QThread(self)
        self._renderer = PageRenderer(self._doc, self._page_index, self._zoom)
        self._renderer.moveToThread(self._render_thread)
        self._renderer.done.connect(self._on_render_done)
        self._render_thread.started.connect(self._renderer.run)
        self._render_thread.start()

    def _on_render_done(self, index: int, pixmap: QPixmap, zoom_at_render: float):
        if zoom_at_render != self._zoom or index != self._page_index:
            return  # descarta se zoom ou página mudou durante render

        self._scene.clear()
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._scene.addItem(self._pixmap_item)
        self._scene.setSceneRect(QRectF(self._pixmap_item.boundingRect()))

        # Centraliza horizontalmente
        self.centerOn(self._pixmap_item)
        self.page_changed.emit(self._page_index + 1, len(self._doc))
        self.zoom_changed.emit(self._zoom)

        if self._render_thread:
            self._render_thread.quit()

    # ------------------------------------------------------------------ Navegação

    def go_to(self, page_index: int):
        if 0 <= page_index < len(self._doc):
            self._page_index = page_index
            self._render_page()
            self.verticalScrollBar().setValue(0)

    def next_page(self):
        self.go_to(self._page_index + 1)

    def prev_page(self):
        self.go_to(self._page_index - 1)

    @property
    def current_page(self) -> int:
        return self._page_index + 1

    @property
    def total_pages(self) -> int:
        return len(self._doc)

    # ------------------------------------------------------------------ Zoom

    def set_zoom(self, zoom: float):
        self._zoom = max(0.25, min(zoom, 5.0))
        self._render_page()

    def zoom_in(self):
        self.set_zoom(self._zoom + 0.25)

    def zoom_out(self):
        self.set_zoom(self._zoom - 0.25)

    def zoom_reset(self):
        self.set_zoom(1.5)

    @property
    def zoom(self) -> float:
        return self._zoom

    # ------------------------------------------------------------------ Scroll contínuo entre páginas

    def wheelEvent(self, event: QWheelEvent):
        # Ctrl+Scroll → zoom
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            self.set_zoom(self._zoom + (0.15 if delta > 0 else -0.15))
            return

        # Scroll normal
        delta = event.angleDelta().y()
        vbar  = self.verticalScrollBar()

        # Borda inferior → próxima página
        if delta < 0 and vbar.value() == vbar.maximum():
            if self._page_index < len(self._doc) - 1:
                self.go_to(self._page_index + 1)
                return

        # Borda superior → página anterior
        if delta > 0 and vbar.value() == vbar.minimum():
            if self._page_index > 0:
                self.go_to(self._page_index - 1)
                vbar.setValue(vbar.maximum())
                return

        super().wheelEvent(event)