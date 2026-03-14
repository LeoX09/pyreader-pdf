import tkinter as tk
from PIL import ImageTk, Image


class PDFCanvas(tk.Frame):
    """Área de exibição do PDF com scroll."""

    def __init__(self, parent, on_scroll=None):
        super().__init__(parent, bg="#1e1e1e")

        self._on_scroll = on_scroll
        self._tk_img = None  # mantém referência para evitar garbage collection
        self._build()

    def _build(self):
        self.canvas = tk.Canvas(self, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.bind("<MouseWheel>", self._handle_scroll)

    def _handle_scroll(self, event):
        if self._on_scroll:
            self._on_scroll(event)
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def display(self, image: Image.Image):
        """Exibe uma imagem PIL no canvas."""
        self._tk_img = ImageTk.PhotoImage(image)

        self.canvas.delete("all")
        canvas_w = self.canvas.winfo_width() or 900
        x = max(canvas_w // 2, image.width // 2)
        self.canvas.create_image(x, 10, anchor=tk.N, image=self._tk_img)
        self.canvas.config(scrollregion=(0, 0, image.width, image.height + 20))

    def scroll(self, delta: int):
        self.canvas.yview_scroll(delta, "units")
