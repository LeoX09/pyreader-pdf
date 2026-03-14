import tkinter as tk
from tkinter import messagebox

from core.document import PDFDocument
from ui.canvas import PDFCanvas
from ui.continuous_canvas import ContinuousCanvas

MODE_SINGLE     = "single"
MODE_CONTINUOUS = "continuous"


class PDFTab(tk.Frame):
    """Conteúdo de uma aba de PDF — modo página única e contínuo."""

    def __init__(self, parent, path: str, on_status_change=None):
        super().__init__(parent, bg="#1e1e1e")

        self.path       = path
        self.filename   = path.replace("\\", "/").split("/")[-1]
        self.on_status_change = on_status_change

        self.doc        = PDFDocument()
        self._view_mode = MODE_SINGLE
        self._continuous_canvas = None

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

    def _open(self, path: str):
        try:
            self.doc.open(path)
            self._render()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o arquivo.\n{e}")

    # ------------------------------------------------------------------ Modo de visualização

    def set_view_mode(self, mode: str):
        if mode == self._view_mode:
            return
        self._view_mode = mode
        self.single_canvas.pack_forget()
        if self._continuous_canvas:
            self._continuous_canvas.pack_forget()

        if mode == MODE_SINGLE:
            self.single_canvas.pack(fill=tk.BOTH, expand=True)
            self._render()
        else:
            self._show_continuous()

    @property
    def view_mode(self) -> str:
        return self._view_mode

    def _show_continuous(self):
        if self._continuous_canvas:
            self._continuous_canvas.destroy()
        self._continuous_canvas = ContinuousCanvas(
            self,
            doc=self.doc,
            on_zoom=self._handle_zoom_continuous,
            on_page_change=lambda i: self._notify_status(),
        )
        self._continuous_canvas.pack(fill=tk.BOTH, expand=True)
        self._continuous_canvas.load()

    # ------------------------------------------------------------------ Render

    def _render(self, scroll_to_bottom: bool = False):
        if not self.doc.is_open or self._view_mode == MODE_CONTINUOUS:
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
                self.doc.zoom,
            )

    # ------------------------------------------------------------------ Navegação

    def next_page(self):
        if self._view_mode == MODE_CONTINUOUS and self._continuous_canvas:
            idx = min(self.doc.page_index + 1, self.doc.total_pages - 1)
            self._continuous_canvas.go_to_page(idx)
        elif self.doc.next_page():
            self._render()

    def prev_page(self):
        if self._view_mode == MODE_CONTINUOUS and self._continuous_canvas:
            idx = max(self.doc.page_index - 1, 0)
            self._continuous_canvas.go_to_page(idx)
        elif self.doc.prev_page():
            self._render()

    def go_to(self, page: int) -> bool:
        if self._view_mode == MODE_CONTINUOUS and self._continuous_canvas:
            if 0 <= page - 1 < self.doc.total_pages:
                self._continuous_canvas.go_to_page(page - 1)
                return True
            return False
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

    def _scroll_next_page(self):
        if self.doc.next_page():
            self._render()
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

    def _handle_zoom_continuous(self, delta: int):
        if delta > 0:
            self.doc.zoom_in()
        else:
            self.doc.zoom_out()
        if self._continuous_canvas:
            self._continuous_canvas.reload_zoom()
        self._notify_status()

    def zoom_in(self):
        self.doc.zoom_in()
        if self._view_mode == MODE_CONTINUOUS and self._continuous_canvas:
            self._continuous_canvas.reload_zoom()
        else:
            self._render()

    def zoom_out(self):
        self.doc.zoom_out()
        if self._view_mode == MODE_CONTINUOUS and self._continuous_canvas:
            self._continuous_canvas.reload_zoom()
        else:
            self._render()

    def zoom_reset(self):
        self.doc.zoom_reset()
        if self._view_mode == MODE_CONTINUOUS and self._continuous_canvas:
            self._continuous_canvas.reload_zoom()
        else:
            self._render()