import tkinter as tk
from tkinter import filedialog, messagebox

from core.document import PDFDocument
from ui.toolbar import Toolbar
from ui.canvas import PDFCanvas
from ui.statusbar import Statusbar


class App:
    """Classe principal — conecta a interface com a lógica do documento."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PyReader")
        self.root.geometry("900x700")
        self.root.configure(bg="#1e1e1e")

        self.doc = PDFDocument()

        self._build_ui()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        callbacks = {
            "open":       self.open_file,
            "prev":       self.prev_page,
            "next":       self.next_page,
            "go_to":      self.go_to_page,
            "zoom_in":    self.zoom_in,
            "zoom_out":   self.zoom_out,
            "zoom_reset": self.zoom_reset,
        }

        self.toolbar = Toolbar(self.root, callbacks)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        self.statusbar = Statusbar(self.root)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = PDFCanvas(self.root)
        self.canvas.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------ Ações

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Selecionar PDF",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if not path:
            return

        try:
            self.doc.open(path)
            filename = path.split("/")[-1].split("\\")[-1]
            self.root.title(f"PyReader — {filename}")
            self.toolbar.update_page(1, self.doc.total_pages)
            self._render()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o arquivo.\n{e}")

    def _render(self):
        """Renderiza a página atual e atualiza a interface."""
        if not self.doc.is_open:
            return
        image = self.doc.render_current_page()
        self.canvas.display(image)
        self.toolbar.update_page(self.doc.page_index + 1, self.doc.total_pages)
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
                messagebox.showwarning("Aviso", f"Página inválida. O documento tem {self.doc.total_pages} páginas.")
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
