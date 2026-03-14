import tkinter as tk
from PIL import ImageTk
import threading


class ContinuousCanvas(tk.Frame):
    """
    Visualização contínua — todas as páginas empilhadas verticalmente.
    Usa lazy loading: só renderiza páginas próximas da área visível.
    """

    PAGE_GAP = 12          # espaço entre páginas (px)
    PRELOAD_MARGIN = 800   # px acima/abaixo da viewport para pré-carregar

    def __init__(self, parent, doc, on_zoom=None, on_page_change=None):
        super().__init__(parent, bg="#181818")

        self._doc = doc
        self._on_zoom = on_zoom
        self._on_page_change = on_page_change  # callback(page_index)

        self._page_images = {}    # page_index -> ImageTk.PhotoImage
        self._page_items = {}     # page_index -> canvas item id
        self._page_tops = []      # y inicial de cada página (calculado)
        self._page_heights = []   # altura renderizada de cada página
        self._loading = set()     # páginas em processo de carregamento
        self._current_page = 0

        self._build()

    # ------------------------------------------------------------------ UI

    def _build(self):
        self.canvas = tk.Canvas(self, bg="#181818", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL,
                                       command=self._on_scroll_command)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self._scrollbar.set)

        self.canvas.bind("<MouseWheel>", self._handle_scroll)
        self.canvas.bind("<Configure>", self._on_resize)

    # ------------------------------------------------------------------ Inicialização

    def load(self):
        """Carrega o documento — calcula layout e renderiza páginas iniciais."""
        if not self._doc.is_open:
            return

        self._page_images.clear()
        self._page_items.clear()
        self._page_tops.clear()
        self._page_heights.clear()
        self._loading.clear()
        self.canvas.delete("all")

        self._calculate_layout()
        self._update_scrollregion()
        self.canvas.after(50, self._lazy_load)

    def _calculate_layout(self):
        """Calcula a posição Y de cada página com base no zoom atual."""
        import fitz
        y = self.PAGE_GAP
        for i in range(self._doc.total_pages):
            page = self._doc._doc[i]
            w = int(page.rect.width * self._doc.zoom)
            h = int(page.rect.height * self._doc.zoom)
            self._page_tops.append(y)
            self._page_heights.append(h)
            y += h + self.PAGE_GAP

    def _total_height(self) -> int:
        if not self._page_tops:
            return 0
        return self._page_tops[-1] + self._page_heights[-1] + self.PAGE_GAP

    def _update_scrollregion(self):
        canvas_w = max(self.canvas.winfo_width(), 800)
        self.canvas.config(scrollregion=(0, 0, canvas_w, self._total_height()))

    # ------------------------------------------------------------------ Lazy loading

    def _lazy_load(self):
        """Renderiza páginas visíveis + margem de pré-carregamento."""
        if not self._doc.is_open or not self._page_tops:
            return

        # Viewport em coordenadas do canvas
        view = self.canvas.yview()
        total_h = self._total_height()
        top_y    = view[0] * total_h - self.PRELOAD_MARGIN
        bottom_y = view[1] * total_h + self.PRELOAD_MARGIN

        for i in range(self._doc.total_pages):
            page_top    = self._page_tops[i]
            page_bottom = page_top + self._page_heights[i]

            in_view = page_bottom >= top_y and page_top <= bottom_y

            if in_view and i not in self._page_images and i not in self._loading:
                self._load_page(i)

    def _load_page(self, index: int):
        """Renderiza uma página em thread separada."""
        self._loading.add(index)

        def render():
            try:
                import fitz
                page = self._doc._doc[index]
                mat = fitz.Matrix(self._doc.zoom, self._doc.zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                from PIL import Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                self.canvas.after(0, lambda: self._place_page(index, img))
            except Exception:
                self._loading.discard(index)

        threading.Thread(target=render, daemon=True).start()

    def _place_page(self, index: int, img):
        """Coloca a página renderizada no canvas (roda na thread principal)."""
        if not self._doc.is_open:
            return

        photo = ImageTk.PhotoImage(img)
        self._page_images[index] = photo
        self._loading.discard(index)

        canvas_w = self.canvas.winfo_width() or 800
        x = max(canvas_w // 2, img.width // 2)
        y = self._page_tops[index]

        # Remove item anterior se existia (ex: após zoom)
        if index in self._page_items:
            self.canvas.delete(self._page_items[index])

        item_id = self.canvas.create_image(x, y, anchor=tk.N, image=photo)
        self._page_items[index] = item_id

    # ------------------------------------------------------------------ Scroll

    def _on_scroll_command(self, *args):
        self.canvas.yview(*args)
        self._after_scroll()

    def _after_scroll(self):
        self._lazy_load()
        self._update_current_page()

    def _handle_scroll(self, event):
        # Ctrl + Scroll = zoom
        if event.state & 0x0004:
            delta = 1 if event.delta > 0 else -1
            if self._on_zoom:
                self._on_zoom(delta)
            return

        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self._after_scroll()

    def _update_current_page(self):
        """Detecta qual página está mais visível e notifica."""
        if not self._page_tops:
            return

        view = self.canvas.yview()
        total_h = self._total_height()
        mid_y = (view[0] + view[1]) / 2 * total_h

        current = 0
        for i, top in enumerate(self._page_tops):
            if top <= mid_y:
                current = i
            else:
                break

        if current != self._current_page:
            self._current_page = current
            self._doc.page_index = current
            if self._on_page_change:
                self._on_page_change(current)

    # ------------------------------------------------------------------ Navegação

    def go_to_page(self, index: int):
        """Salta para uma página pelo índice (0-based)."""
        if not self._page_tops or index >= len(self._page_tops):
            return
        total_h = self._total_height()
        if total_h == 0:
            return
        frac = self._page_tops[index] / total_h
        self.canvas.yview_moveto(frac)
        self._current_page = index
        self._doc.page_index = index
        self._lazy_load()

    # ------------------------------------------------------------------ Zoom

    def reload_zoom(self):
        """Recalcula layout e recarrega todas as páginas após mudança de zoom."""
        current = self._current_page
        self._page_images.clear()
        self._page_items.clear()
        self._page_tops.clear()
        self._page_heights.clear()
        self._loading.clear()
        self.canvas.delete("all")
        self._calculate_layout()
        self._update_scrollregion()
        self.canvas.after(30, lambda: self.go_to_page(current))
        self.canvas.after(60, self._lazy_load)

    # ------------------------------------------------------------------ Resize

    def _on_resize(self, event):
        self._update_scrollregion()
        # Reposiciona itens já renderizados
        for index, item_id in self._page_items.items():
            if index in self._page_images:
                img = self._page_images[index]
                canvas_w = event.width
                # Calcula largura da imagem a partir do item
                x = max(canvas_w // 2,
                        getattr(img, 'width', canvas_w // 2))
                self.canvas.coords(item_id, x, self._page_tops[index])
        self._lazy_load()