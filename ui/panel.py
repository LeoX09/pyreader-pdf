import tkinter as tk
from tkinter import filedialog, messagebox

from core.document import PDFDocument
from ui.canvas import PDFCanvas


class Panel(tk.Frame):
    """Painel independente com seu próprio documento, navegação e zoom."""

    def __init__(self, parent, panel_id: str, on_status_change=None):
        super().__init__(parent, bg="#1e1e1e")

        self.panel_id = panel_id
        self.on_status_change = on_status_change  # callback para atualizar statusbar
        self.doc = PDFDocument()
        self.sync_scroll = False
        self.sync_callback = None  # chamado quando o painel faz scroll sincronizado

        self._build()

    # ------------------------------------------------------------------ UI

    def _build(self):
        self._build_panel_toolbar()
        self.canvas = PDFCanvas(self, on_scroll=self._handle_scroll)
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def _build_panel_toolbar(self):
        bar = tk.Frame(self, bg="#252525", pady=4)
        bar.pack(side=tk.TOP, fill=tk.X)

        btn = {"bg": "#3a3a3a", "fg": "white", "relief": "flat",
               "padx": 8, "pady": 3, "cursor": "hand2",
               "activebackground": "#505050", "activeforeground": "white",
               "font": ("Arial", 9)}

        tk.Button(bar, text="Abrir", command=self.open_file, **btn).pack(side=tk.LEFT, padx=(6, 2))

        tk.Frame(bar, bg="#555", width=1).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        tk.Button(bar, text="◀", command=self.prev_page, **btn).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="▶", command=self.next_page, **btn).pack(side=tk.LEFT, padx=2)

        tk.Frame(bar, bg="#555", width=1).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        self.page_entry = tk.Entry(bar, width=4, bg="#3a3a3a", fg="white",
                                   insertbackground="white", relief="flat",
                                   font=("Arial", 9))
        self.page_entry.pack(side=tk.LEFT, padx=(0, 2))
        self.page_entry.bind("<Return>", self.go_to_page)

        self.total_label = tk.Label(bar, text="/ -", bg="#252525", fg="#aaa", font=("Arial", 9))
        self.total_label.pack(side=tk.LEFT)

        tk.Frame(bar, bg="#555", width=1).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        tk.Button(bar, text="−", command=self.zoom_out,   **btn).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="+", command=self.zoom_in,    **btn).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="↺", command=self.zoom_reset, **btn).pack(side=tk.LEFT, padx=2)

        # label do painel (ex: "Painel A")
        tk.Label(bar, text=f"Painel {self.panel_id}", bg="#252525",
                 fg="#555", font=("Arial", 8)).pack(side=tk.RIGHT, padx=8)

    # ------------------------------------------------------------------ Ações

    def open_file(self):
        path = filedialog.askopenfilename(
            title=f"Painel {self.panel_id} — Selecionar PDF",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if not path:
            return
        try:
            self.doc.open(path)
            self._render()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o arquivo.\n{e}")

    def open_path(self, path: str):
        """Abre um PDF diretamente por caminho (usado pelo app principal)."""
        try:
            self.doc.open(path)
            self._render()
        except Exception as e:
            messagebox.showerror("Erro", f"Painel {self.panel_id}: {e}")

    def _render(self):
        if not self.doc.is_open:
            return
        image = self.doc.render_current_page()
        self.canvas.display(image)

        current = self.doc.page_index + 1
        total = self.doc.total_pages

        self.page_entry.delete(0, tk.END)
        self.page_entry.insert(0, str(current))
        self.total_label.config(text=f"/ {total}")

        if self.on_status_change:
            self.on_status_change(self.panel_id, current, total, self.doc.zoom)

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
            page = int(self.page_entry.get())
            if self.doc.go_to(page):
                self._render()
            else:
                messagebox.showwarning("Aviso", f"Página inválida. Total: {self.doc.total_pages}")
        except ValueError:
            messagebox.showwarning("Aviso", "Digite um número válido.")

    def zoom_in(self):
        self.doc.zoom_in()
        self._render()

    def zoom_out(self):
        self.doc.zoom_out()
        self._render()

    def zoom_reset(self):
        self.doc.zoom_reset()
        self._render()

    # ------------------------------------------------------------------ Scroll

    def _handle_scroll(self, event):
        delta = int(-1 * (event.delta / 120))
        self.canvas.scroll(delta)
        if self.sync_scroll and self.sync_callback:
            self.sync_callback(delta)

    def scroll_to(self, delta: int):
        """Recebe scroll externo (sincronizado)."""
        self.canvas.scroll(delta)
