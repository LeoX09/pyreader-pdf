import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageTk


class PyReader:
    def __init__(self, root):
        self.root = root
        self.root.title("PyReaderPDF")
        self.root.geometry("900x700")
        self.root.configure(bg="#1e1e1e")

        self.doc = None          # documento PDF aberto
        self.page_index = 0      # página atual (começa em 0)
        self.zoom = 1.5          # fator de zoom padrão

        self._build_toolbar()
        self._build_canvas()
        self._build_statusbar()

    # ------------------------------------------------------------------ UI

    def _build_toolbar(self):
        toolbar = tk.Frame(self.root, bg="#2d2d2d", pady=6)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        btn_style = {"bg": "#3a3a3a", "fg": "white", "relief": "flat",
                     "padx": 10, "pady": 4, "cursor": "hand2",
                     "activebackground": "#505050", "activeforeground": "white"}

        tk.Button(toolbar, text="Abrir PDF", command=self.open_file, **btn_style).pack(side=tk.LEFT, padx=(8, 4))

        tk.Frame(toolbar, bg="#555", width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        tk.Button(toolbar, text="◀ Anterior", command=self.prev_page, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Próxima ▶", command=self.next_page, **btn_style).pack(side=tk.LEFT, padx=2)

        tk.Frame(toolbar, bg="#555", width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        tk.Label(toolbar, text="Página:", bg="#2d2d2d", fg="#aaa").pack(side=tk.LEFT)
        self.page_entry = tk.Entry(toolbar, width=5, bg="#3a3a3a", fg="white",
                                   insertbackground="white", relief="flat")
        self.page_entry.pack(side=tk.LEFT, padx=(4, 2))
        self.page_entry.bind("<Return>", self.go_to_page)
        self.total_label = tk.Label(toolbar, text="/ -", bg="#2d2d2d", fg="#aaa")
        self.total_label.pack(side=tk.LEFT)

        tk.Frame(toolbar, bg="#555", width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        tk.Button(toolbar, text="Zoom −", command=self.zoom_out, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Zoom +", command=self.zoom_in,  **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="100%",   command=self.zoom_reset, **btn_style).pack(side=tk.LEFT, padx=2)

    def _build_canvas(self):
        frame = tk.Frame(self.root, bg="#1e1e1e")
        frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(frame, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # scroll com roda do mouse
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

    def _build_statusbar(self):
        self.statusbar = tk.Label(self.root, text="Nenhum arquivo aberto",
                                  bg="#2d2d2d", fg="#888", anchor=tk.W, padx=10)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------------------------------------------------------ AÇÕES

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Selecionar PDF",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if not path:
            return

        try:
            self.doc = fitz.open(path)
            self.page_index = 0
            self.root.title(f"PyReader — {path.split('/')[-1]}")
            self.total_label.config(text=f"/ {len(self.doc)}")
            self._render_page()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o arquivo.\n{e}")

    def _render_page(self):
        if self.doc is None:
            return

        page = self.doc[self.page_index]
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.tk_img = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        # centraliza a imagem no canvas
        canvas_w = self.canvas.winfo_width() or 900
        x = max(canvas_w // 2, pix.width // 2)
        self.canvas.create_image(x, 10, anchor=tk.N, image=self.tk_img)
        self.canvas.config(scrollregion=(0, 0, pix.width, pix.height + 20))

        # atualiza campos de status
        self.page_entry.delete(0, tk.END)
        self.page_entry.insert(0, str(self.page_index + 1))
        self.statusbar.config(
            text=f"Página {self.page_index + 1} de {len(self.doc)}  |  Zoom: {int(self.zoom * 100)}%"
        )

    def next_page(self):
        if self.doc and self.page_index < len(self.doc) - 1:
            self.page_index += 1
            self._render_page()

    def prev_page(self):
        if self.doc and self.page_index > 0:
            self.page_index -= 1
            self._render_page()

    def go_to_page(self, event=None):
        if not self.doc:
            return
        try:
            n = int(self.page_entry.get()) - 1
            if 0 <= n < len(self.doc):
                self.page_index = n
                self._render_page()
            else:
                messagebox.showwarning("Aviso", f"Página inválida. O documento tem {len(self.doc)} páginas.")
        except ValueError:
            messagebox.showwarning("Aviso", "Digite um número de página válido.")

    def zoom_in(self):
        self.zoom = min(self.zoom + 0.25, 4.0)
        self._render_page()

    def zoom_out(self):
        self.zoom = max(self.zoom - 0.25, 0.5)
        self._render_page()

    def zoom_reset(self):
        self.zoom = 1.5
        self._render_page()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ------------------------------------------------------------------ MAIN

if __name__ == "__main__":
    root = tk.Tk()
    app = PyReader(root)
    root.mainloop()