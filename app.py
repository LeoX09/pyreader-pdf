import tkinter as tk
from tkinter import filedialog, messagebox

from core.document import PDFDocument
from ui.toolbar import Toolbar
from ui.canvas import PDFCanvas
from ui.statusbar import Statusbar
from ui.splitview import SplitView


class App:
    """Classe principal — gerencia modo único e modo Split View."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PyReaderPDF")
        self.root.geometry("1100x750")
        self.root.configure(bg="#1e1e1e")

        self.doc = PDFDocument()
        self._split_active = False
        self._sync_active = False

        self._build_ui()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        callbacks = {
            "open":          self.open_file,
            "prev":          self.prev_page,
            "next":          self.next_page,
            "go_to":         self.go_to_page,
            "zoom_in":       self.zoom_in,
            "zoom_out":      self.zoom_out,
            "zoom_reset":    self.zoom_reset,
            "toggle_split":  self.toggle_split,
            "toggle_sync":   self.toggle_sync,
        }

        self.toolbar = Toolbar(self.root, callbacks)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        self.statusbar = Statusbar(self.root)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Área de conteúdo — troca entre modo único e split
        self.content_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Modo único
        self.single_canvas = PDFCanvas(
            self.content_frame,
            on_zoom=self._handle_zoom,
            on_page_end=self._scroll_next_page,
            on_page_start=self._scroll_prev_page,
        )
        self.single_canvas.pack(fill=tk.BOTH, expand=True)

        # Split View (começa oculto)
        self.split_view = SplitView(self.content_frame,
                                    on_status_change=self._on_panel_status_change)

    # ------------------------------------------------------------------ Modo único

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Selecionar PDF",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if not path:
            return
        try:
            self.doc.open(path)
            filename = path.replace("\\", "/").split("/")[-1]
            self.root.title(f"PyReaderPDF — {filename}")
            self.toolbar.update_page(1, self.doc.total_pages)
            self._render()

            # se split view estiver ativo, abre nos dois painéis
            if self._split_active:
                self.split_view.open_in_both(path)

        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o arquivo.\n{e}")

    def _render(self, scroll_to_bottom: bool = False):
        if not self.doc.is_open or self._split_active:
            return
        image = self.doc.render_current_page()
        self.single_canvas.display(image)
        if scroll_to_bottom:
            self.single_canvas.scroll_to_bottom()
        else:
            self.single_canvas.scroll_to_top()
        self.toolbar.update_page(self.doc.page_index + 1, self.doc.total_pages)
        self.statusbar.update(self.doc.page_index + 1, self.doc.total_pages, self.doc.zoom)

    def _scroll_next_page(self):
        if self.doc.next_page():
            self._render(scroll_to_bottom=False)

    def _scroll_prev_page(self):
        if self.doc.prev_page():
            self._render(scroll_to_bottom=True)

    def _handle_zoom(self, delta: int):
        if delta > 0:
            self.doc.zoom_in()
        else:
            self.doc.zoom_out()
        if self.doc.is_open:
            image = self.doc.render_current_page()
            self.single_canvas.display(image, keep_position=True)
            self.statusbar.update(self.doc.page_index + 1, self.doc.total_pages, self.doc.zoom)

    def next_page(self):
        if self.doc.next_page():
            self._render()

    def prev_page(self):
        if self.doc.prev_page():
            self._render()

    def go_to_page(self, event=None):
        if not self.doc.is_open:
            return
        try:
            page = int(self.toolbar.get_page_input())
            if self.doc.go_to(page):
                self._render()
            else:
                messagebox.showwarning("Aviso", f"Página inválida. Total: {self.doc.total_pages}")
        except ValueError:
            messagebox.showwarning("Aviso", "Digite um número de página válido.")

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

    def toggle_split(self):
        self._split_active = not self._split_active

        if self._split_active:
            self.single_canvas.pack_forget()
            self.split_view.pack(fill=tk.BOTH, expand=True)

            # se já tiver um arquivo aberto, carrega nos dois painéis
            if self.doc.is_open:
                import fitz
                path = self.doc._doc.name
                self.split_view.open_in_both(path)

            self.statusbar.set_message("Split View ativo — cada painel tem navegação independente")
        else:
            self.split_view.pack_forget()
            self.single_canvas.pack(fill=tk.BOTH, expand=True)
            self._sync_active = False
            self.split_view.set_sync_scroll(False)
            self.toolbar.set_sync_active(False)
            self._render()

        self.toolbar.set_split_active(self._split_active)

    def toggle_sync(self):
        if not self._split_active:
            return
        self._sync_active = not self._sync_active
        self.split_view.set_sync_scroll(self._sync_active)
        self.toolbar.set_sync_active(self._sync_active)

        msg = "Scroll sincronizado ativado" if self._sync_active else "Scroll sincronizado desativado"
        self.statusbar.set_message(msg)

    def _on_panel_status_change(self, panel_id: str, current: int, total: int, zoom: float):
        """Atualiza a statusbar quando um painel muda de página."""
        self.statusbar.set_message(
            f"Painel {panel_id} — Página {current} de {total}  |  Zoom: {int(zoom * 100)}%"
        )