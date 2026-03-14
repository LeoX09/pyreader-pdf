import tkinter as tk
from tkinter import messagebox

from core.document import PDFDocument
from ui.canvas import PDFCanvas
from ui.continuous_canvas import ContinuousCanvas
from ui.splitview import SplitView

MODE_SINGLE     = "single"
MODE_CONTINUOUS = "continuous"


class PDFTab(tk.Frame):
    """Conteúdo de uma aba de PDF — suporta modo página única e contínuo."""

    def __init__(self, parent, path: str, on_status_change=None):
        super().__init__(parent, bg="#1e1e1e")

        self.path = path
        self.filename = path.replace("\\", "/").split("/")[-1]
        self.on_status_change = on_status_change

        self.doc = PDFDocument()
        self._view_mode = MODE_SINGLE
        self._split_active = False
        self._sync_active = False

        self._build()
        self._open(path)

    # ------------------------------------------------------------------ UI

    def _build(self):
        # Modo página única
        self.single_canvas = PDFCanvas(
            self,
            on_zoom=self._handle_zoom,
            on_page_end=self._scroll_next_page,
            on_page_start=self._scroll_prev_page,
        )

        # Modo contínuo (criado após abrir o doc)
        self._continuous_canvas = None

        # Split view
        self.split_view = SplitView(self, on_status_change=self._on_panel_status)

        # Começa no modo único
        self.single_canvas.pack(fill=tk.BOTH, expand=True)

    def _open(self, path: str):
        try:
            self.doc.open(path)
            self._render()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o arquivo.\n{e}")

    # ------------------------------------------------------------------ Modo de visualização

    def set_view_mode(self, mode: str):
        """Alterna entre MODE_SINGLE e MODE_CONTINUOUS."""
        if mode == self._view_mode:
            return
        if self._split_active:
            return  # split view tem seus próprios modos

        self._view_mode = mode

        # Oculta tudo
        self.single_canvas.pack_forget()
        if self._continuous_canvas:
            self._continuous_canvas.pack_forget()

        if mode == MODE_SINGLE:
            self.single_canvas.pack(fill=tk.BOTH, expand=True)
            self._render()
        else:
            self._show_continuous()

    def _show_continuous(self):
        if self._continuous_canvas:
            self._continuous_canvas.destroy()

        self._continuous_canvas = ContinuousCanvas(
            self,
            doc=self.doc,
            on_zoom=self._handle_zoom_continuous,
            on_page_change=self._on_continuous_page_change,
        )
        self._continuous_canvas.pack(fill=tk.BOTH, expand=True)
        self._continuous_canvas.load()

    @property
    def view_mode(self) -> str:
        return self._view_mode

    # ------------------------------------------------------------------ Render (modo único)

    def _render(self, scroll_to_bottom: bool = False):
        if not self.doc.is_open or self._split_active:
            return
        if self._view_mode == MODE_CONTINUOUS:
            return  # contínuo se auto-gerencia
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
        if self._view_mode == MODE_CONTINUOUS:
            if self._continuous_canvas:
                idx = min(self.doc.page_index + 1, self.doc.total_pages - 1)
                self._continuous_canvas.go_to_page(idx)
        else:
            if self.doc.next_page():
                self._render()

    def prev_page(self):
        if self._view_mode == MODE_CONTINUOUS:
            if self._continuous_canvas:
                idx = max(self.doc.page_index - 1, 0)
                self._continuous_canvas.go_to_page(idx)
        else:
            if self.doc.prev_page():
                self._render()

    def go_to(self, page: int):
        index = page - 1
        if self._view_mode == MODE_CONTINUOUS:
            if self._continuous_canvas and 0 <= index < self.doc.total_pages:
                self._continuous_canvas.go_to_page(index)
                return True
            return False
        else:
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

    # ------------------------------------------------------------------ Scroll contínuo (modo único)

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

    # ------------------------------------------------------------------ Callback contínuo

    def _on_continuous_page_change(self, index: int):
        self._notify_status()

    # ------------------------------------------------------------------ Split View

    def toggle_split(self) -> bool:
        self._split_active = not self._split_active
        if self._split_active:
            self.single_canvas.pack_forget()
            if self._continuous_canvas:
                self._continuous_canvas.pack_forget()
            self.split_view.pack(fill=tk.BOTH, expand=True)
            self.split_view.open_in_both(self.path)
        else:
            self.split_view.pack_forget()
            self._sync_active = False
            self.split_view.set_sync_scroll(False)
            # Restaura o modo de visualização atual
            if self._view_mode == MODE_CONTINUOUS:
                self._show_continuous()
            else:
                self.single_canvas.pack(fill=tk.BOTH, expand=True)
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