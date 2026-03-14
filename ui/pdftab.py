import tkinter as tk
from tkinter import messagebox

from core.document import PDFDocument
from ui.canvas import PDFCanvas
from ui.splitview import SplitView


class PDFTab(tk.Frame):
    """Conteúdo de uma aba de PDF — documento, canvas e split view."""

    def __init__(self, parent, path: str, on_status_change=None):
        super().__init__(parent, bg="#1e1e1e")

        self.path = path
        self.filename = path.replace("\\", "/").split("/")[-1]
        self.on_status_change = on_status_change

        self.doc = PDFDocument()
        self._split_active = False
        self._sync_active = False

        self._build()
        self._open(path)

    # ------------------------------------------------------------------ UI

    def _build(self):
        self.single_canvas = PDFCanvas(
            self,
            on_zoom=self._handle_zoom,
            on_page_end=self._scroll_next_page,
            on_page_start=self._scroll_prev_page,
        )
        self.single_canvas.pack(fill=tk.BOTH, expand=True)

        self.split_view = SplitView(self, on_status_change=self._on_panel_status)

    def _open(self, path: str):
        try:
            self.doc.open(path)
            self._render()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o arquivo.\n{e}")

    # ------------------------------------------------------------------ Render

    def _render(self, scroll_to_bottom: bool = False):
        if not self.doc.is_open or self._split_active:
            return
        image = self.doc.render_current_page()
        self.single_canvas.display(image)
        if scroll_to_bottom:
            self.single_canvas.scroll_to_bottom()
        else:
            self.single_canvas.scroll_to_top()
        self._notify_status()

    def _notify_status(self):
        if self.on_status_change and self.doc.is_open:
            self.on_status_change(
                self.doc.page_index + 1,
                self.doc.total_pages,
                self.doc.zoom
            )

    # ------------------------------------------------------------------ Navegação

    def next_page(self):
        if self.doc.next_page():
            self._render()

    def prev_page(self):
        if self.doc.prev_page():
            self._render()

    def go_to(self, page: int):
        if self.doc.go_to(page):
            self._render()
            return True
        return False

    @property
    def current_page(self) -> int:
        return self.doc.page_index + 1

    @property
    def total_pages(self) -> int:
        return self.doc.total_pages

    # ------------------------------------------------------------------ Scroll contínuo

    def _scroll_next_page(self):
        if self.doc.next_page():
            self._render(scroll_to_bottom=False)
            self._notify_status()

    def _scroll_prev_page(self):
        if self.doc.prev_page():
            self._render(scroll_to_bottom=True)
            self._notify_status()

    # ------------------------------------------------------------------ Zoom

    def _handle_zoom(self, delta: int):
        if delta > 0:
            self.doc.zoom_in()
        else:
            self.doc.zoom_out()
        if self.doc.is_open:
            image = self.doc.render_current_page()
            self.single_canvas.display(image, keep_position=True)
            self._notify_status()

    def zoom_in(self):
        self.doc.zoom_in()
        self._render()

    def zoom_out(self):
        self.doc.zoom_out()
        self._render()

    def zoom_reset(self):
        self.doc.zoom_reset()
        self._render()

    # ------------------------------------------------------------------ Split View

    def toggle_split(self) -> bool:
        self._split_active = not self._split_active
        if self._split_active:
            self.single_canvas.pack_forget()
            self.split_view.pack(fill=tk.BOTH, expand=True)
            self.split_view.open_in_both(self.path)
        else:
            self.split_view.pack_forget()
            self.single_canvas.pack(fill=tk.BOTH, expand=True)
            self._sync_active = False
            self.split_view.set_sync_scroll(False)
            self._render()
        return self._split_active

    def toggle_sync(self) -> bool:
        if not self._split_active:
            return False
        self._sync_active = not self._sync_active
        self.split_view.set_sync_scroll(self._sync_active)
        return self._sync_active

    @property
    def split_active(self) -> bool:
        return self._split_active

    @property
    def sync_active(self) -> bool:
        return self._sync_active

    def _on_panel_status(self, panel_id, current, total, zoom):
        if self.on_status_change:
            self.on_status_change(current, total, zoom)