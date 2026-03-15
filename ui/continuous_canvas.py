import tkinter as tk
from PIL import ImageTk, Image
import threading


class ContinuousCanvas(tk.Frame):
    PAGE_GAP        = 12
    PRELOAD_MARGIN  = 800
    HIRES_DELAY_MS  = 300

    def __init__(self, parent, doc, on_zoom=None, on_page_change=None):
        super().__init__(parent, bg="#181818")
        self._doc            = doc
        self._on_zoom        = on_zoom
        self._on_page_change = on_page_change
        self._source_images  = {}
        self._page_photos    = {}
        self._page_items     = {}
        self._page_tops      = []
        self._page_heights   = []
        self._loading        = set()
        self._stale_pages    = set()  # páginas com zoom desatualizado, aguardando hi-res
        self._current_page   = 0
        self._hires_timer    = None
        self._build()

    def _build(self):
        self.canvas = tk.Canvas(self, bg="#181818", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(self, orient=tk.VERTICAL, command=self._on_scroll_cmd)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.bind("<MouseWheel>", self._handle_scroll)
        self.canvas.bind("<Configure>",  self._on_resize)

    def load(self):
        self._source_images.clear()
        self._page_photos.clear()
        self._page_items.clear()
        self._page_tops.clear()
        self._page_heights.clear()
        self._loading.clear()
        self._stale_pages.clear()
        self.canvas.delete("all")
        self._calculate_layout()
        self._update_scrollregion()
        self.canvas.after(50, self._lazy_load)

    def _calculate_layout(self):
        import fitz
        y = self.PAGE_GAP
        for i in range(self._doc.total_pages):
            page = self._doc._doc[i]
            self._page_tops.append(y)
            h = int(page.rect.height * self._doc.zoom)
            self._page_heights.append(h)
            y += h + self.PAGE_GAP

    def _total_height(self):
        if not self._page_tops:
            return 0
        return self._page_tops[-1] + self._page_heights[-1] + self.PAGE_GAP

    def _update_scrollregion(self):
        canvas_w = max(self.canvas.winfo_width(), 800)
        self.canvas.config(scrollregion=(0, 0, canvas_w, self._total_height()))

    # ------------------------------------------------------------------ Lazy load

    def _lazy_load(self):
        if not self._doc.is_open or not self._page_tops:
            return
        view    = self.canvas.yview()
        total_h = self._total_height()
        top_y   = view[0] * total_h - self.PRELOAD_MARGIN
        bot_y   = view[1] * total_h + self.PRELOAD_MARGIN
        for i in range(self._doc.total_pages):
            in_view = (self._page_tops[i] + self._page_heights[i] >= top_y and
                       self._page_tops[i] <= bot_y)
            needs_render = i not in self._source_images or i in self._stale_pages
            if in_view and needs_render and i not in self._loading:
                self._render_hires(i)

    def _render_hires(self, index: int):
        self._loading.add(index)
        zoom = self._doc.zoom

        def worker():
            try:
                import fitz
                page = self._doc._doc[index]
                pix  = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                img  = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                self.canvas.after(0, lambda: self._on_hires_ready(index, img, zoom))
            except Exception:
                self._loading.discard(index)

        threading.Thread(target=worker, daemon=True).start()

    def _on_hires_ready(self, index: int, img: Image.Image, zoom_at_render: float):
        self._loading.discard(index)
        if not self._doc.is_open:
            return
        if zoom_at_render != self._doc.zoom:
            return  # zoom mudou enquanto renderizava — descarta
        self._source_images[index] = img
        self._stale_pages.discard(index)  # hi-res atualizada — não é mais stale
        self._put_photo(index, img)

    # ------------------------------------------------------------------ Zoom suave

    def reload_zoom(self):
        current = self._current_page

        # Recalcula layout
        self._page_tops.clear()
        self._page_heights.clear()
        self._calculate_layout()
        self._update_scrollregion()

        # Preview instantâneo das páginas visíveis
        self._apply_instant_preview()

        # Reposiciona tudo
        self._reposition_items()

        # Volta para a página atual
        self.canvas.after(10, lambda: self.go_to_page(current))

        # Agenda hi-res com debounce
        self._schedule_hires_reload()

    def _apply_instant_preview(self):
        """
        Resize NEAREST nas imagens já carregadas — instantâneo.
        Só processa páginas próximas da viewport.
        """
        zoom    = self._doc.zoom
        view    = self.canvas.yview()
        total_h = self._total_height()
        top_y   = view[0] * total_h - 200
        bot_y   = view[1] * total_h + 200

        for index, src in self._source_images.items():
            if index >= len(self._page_tops):
                continue
            in_view = (self._page_tops[index] + self._page_heights[index] >= top_y and
                       self._page_tops[index] <= bot_y)
            if not in_view:
                continue
            try:
                page  = self._doc._doc[index]
                new_w = int(page.rect.width  * zoom)
                new_h = int(page.rect.height * zoom)
                preview = src.resize((new_w, new_h), Image.NEAREST)
                self._put_photo(index, preview)
            except Exception:
                pass

    def _put_photo(self, index: int, img: Image.Image):
        photo = ImageTk.PhotoImage(img)
        self._page_photos[index] = photo
        canvas_w = self.canvas.winfo_width() or 800
        x = max(canvas_w // 2, img.width // 2)
        y = self._page_tops[index] if index < len(self._page_tops) else 0
        if index in self._page_items:
            self.canvas.itemconfig(self._page_items[index], image=photo)
            self.canvas.coords(self._page_items[index], x, y)
        else:
            item_id = self.canvas.create_image(x, y, anchor=tk.N, image=photo)
            self._page_items[index] = item_id

    def _reposition_items(self):
        canvas_w = self.canvas.winfo_width() or 800
        for index, item_id in self._page_items.items():
            if index < len(self._page_tops):
                photo = self._page_photos.get(index)
                x = max(canvas_w // 2, (photo.width() if photo else 400) // 2)
                self.canvas.coords(item_id, x, self._page_tops[index])

    # ------------------------------------------------------------------ Debounce hi-res

    def _schedule_hires_reload(self):
        if self._hires_timer is not None:
            self.canvas.after_cancel(self._hires_timer)
        self._hires_timer = self.canvas.after(self.HIRES_DELAY_MS, self._do_hires_reload)

    def _do_hires_reload(self):
        """
        Marca todas as páginas como stale — precisam de nova hi-res.
        NÃO limpa _source_images: a imagem antiga (preview) continua
        visível na tela até a nova hi-res substituí-la individualmente.
        """
        self._hires_timer = None
        self._stale_pages.update(range(self._doc.total_pages))
        self._loading.clear()
        self._lazy_load()

    # ------------------------------------------------------------------ Scroll

    def _on_scroll_cmd(self, *args):
        self.canvas.yview(*args)
        self._after_scroll()

    def _after_scroll(self):
        self._lazy_load()
        self._update_current_page()

    def _handle_scroll(self, event):
        if event.state & 0x0004:
            delta = 1 if event.delta > 0 else -1
            if self._on_zoom:
                self._on_zoom(delta)
            return
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self._after_scroll()

    def _update_current_page(self):
        if not self._page_tops:
            return
        view    = self.canvas.yview()
        total_h = self._total_height()
        mid_y   = (view[0] + view[1]) / 2 * total_h
        current = 0
        for i, top in enumerate(self._page_tops):
            if top <= mid_y:
                current = i
            else:
                break
        if current != self._current_page:
            self._current_page   = current
            self._doc.page_index = current
            if self._on_page_change:
                self._on_page_change(current)

    # ------------------------------------------------------------------ Navegação

    def go_to_page(self, index: int):
        if not self._page_tops or index >= len(self._page_tops):
            return
        total_h = self._total_height()
        if total_h == 0:
            return
        self.canvas.yview_moveto(self._page_tops[index] / total_h)
        self._current_page   = index
        self._doc.page_index = index
        self._lazy_load()

    # ------------------------------------------------------------------ Resize

    def _on_resize(self, event):
        self._update_scrollregion()
        canvas_w = event.width
        for index, item_id in self._page_items.items():
            photo = self._page_photos.get(index)
            if photo and index < len(self._page_tops):
                x = max(canvas_w // 2, photo.width() // 2)
                self.canvas.coords(item_id, x, self._page_tops[index])
        self._lazy_load()