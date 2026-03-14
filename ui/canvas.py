import tkinter as tk
from PIL import ImageTk, Image


class PDFCanvas(tk.Frame):
    """Área de exibição do PDF com scroll, scroll contínuo e zoom por Ctrl+Scroll."""

    def __init__(self, parent, on_scroll=None, on_zoom=None, on_page_end=None, on_page_start=None):
        super().__init__(parent, bg="#1e1e1e")

        self._on_scroll = on_scroll
        self._on_zoom = on_zoom
        self._on_page_end = on_page_end
        self._on_page_start = on_page_start
        self._tk_img = None
        self._last_image = None
        self._build()

    def _build(self):
        self.canvas = tk.Canvas(self, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.bind("<MouseWheel>", self._handle_scroll)
        self.canvas.bind("<Configure>", self._on_resize)

    # ------------------------------------------------------------------ Resize

    def _on_resize(self, event):
        """Recentraliza a imagem quando o canvas é redimensionado."""
        if self._last_image:
            self._place_image(self._last_image)

    def _place_image(self, image: Image.Image):
        """Posiciona a imagem centralizada horizontalmente no canvas."""
        canvas_w = self.canvas.winfo_width()
        if canvas_w <= 1:
            # Canvas ainda não foi desenhado — tenta novamente em 10ms
            self.canvas.after(10, lambda: self._place_image(image))
            return
        x = max(canvas_w // 2, image.width // 2)
        self.canvas.delete("all")
        self.canvas.create_image(x, 10, anchor=tk.N, image=self._tk_img)
        self.canvas.config(scrollregion=(
            0, 0,
            max(canvas_w, image.width),
            image.height + 20
        ))

    # ------------------------------------------------------------------ Scroll

    def _handle_scroll(self, event):
        if event.state & 0x0004:
            delta = 1 if event.delta > 0 else -1
            if self._on_zoom:
                self._on_zoom(delta)
            return

        delta = int(-1 * (event.delta / 120))

        if delta > 0 and self._on_page_end:
            pos = self.canvas.yview()
            if pos[1] >= 1.0:
                self._on_page_end()
                return

        if delta < 0 and self._on_page_start:
            pos = self.canvas.yview()
            if pos[0] <= 0.0:
                self._on_page_start()
                return

        if self._on_scroll:
            self._on_scroll(event)
        else:
            self.canvas.yview_scroll(delta, "units")

    # ------------------------------------------------------------------ Display

    def display(self, image: Image.Image, keep_position: bool = False):
        pos = self.canvas.yview() if keep_position else None
        self._tk_img = ImageTk.PhotoImage(image)
        self._last_image = image
        self._place_image(image)
        if keep_position and pos:
            self.canvas.yview_moveto(pos[0])

    def scroll_to_bottom(self):
        self.canvas.yview_moveto(1.0)

    def scroll_to_top(self):
        self.canvas.yview_moveto(0.0)

    def scroll(self, delta: int):
        self.canvas.yview_scroll(delta, "units")