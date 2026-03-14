import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
from PIL import Image, ImageTk

from core.library import load_library, add_to_library, remove_from_library, is_in_library
from core.history import load_recent
from core.thumbnail import get_thumbnail

CARD_W = 170
CARD_H = 270
THUMB_W = 150
THUMB_H = 210


class HomeScreen(tk.Frame):
    """Tela inicial — biblioteca de PDFs com capas e arquivos recentes."""

    def __init__(self, parent, on_open):
        super().__init__(parent, bg="#181818")
        self._on_open = on_open
        self._thumb_refs = []   # evita garbage collection das imagens
        self._build()

    # ------------------------------------------------------------------ Layout

    def _build(self):
        # Sidebar esquerda
        sidebar = tk.Frame(self, bg="#141414", width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        # Área principal
        self._main = tk.Frame(self, bg="#181818")
        self._main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._show_library()

    def _build_sidebar(self, parent):
        tk.Label(parent, text="PyReaderPDF", bg="#141414", fg="white",
                 font=("Arial", 13, "bold"), pady=20).pack(anchor=tk.W, padx=20)

        sep = tk.Frame(parent, bg="#2a2a2a", height=1)
        sep.pack(fill=tk.X, padx=16, pady=(0, 12))

        self._btn_library = self._sidebar_btn(parent, "⊟  Biblioteca", self._show_library)
        self._btn_recent  = self._sidebar_btn(parent, "⊙  Recentes",   self._show_recent)

        sep2 = tk.Frame(parent, bg="#2a2a2a", height=1)
        sep2.pack(fill=tk.X, padx=16, pady=12)

        self._sidebar_btn(parent, "+  Adicionar PDF", self.add_to_library,
                          accent=True)

    def _sidebar_btn(self, parent, text, cmd, accent=False):
        bg = "#1a6b3c" if accent else "#141414"
        hover = "#1f8048" if accent else "#232323"
        btn = tk.Label(parent, text=text, bg=bg, fg="white",
                       font=("Arial", 10), anchor=tk.W,
                       padx=20, pady=10, cursor="hand2")
        btn.pack(fill=tk.X)
        btn.bind("<Button-1>", lambda e: cmd())
        btn.bind("<Enter>", lambda e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    # ------------------------------------------------------------------ Seções

    def _clear_main(self):
        for w in self._main.winfo_children():
            w.destroy()
        self._thumb_refs.clear()

    def _show_library(self):
        self._set_active_sidebar(self._btn_library)
        self._clear_main()
        books = load_library()

        header = tk.Frame(self._main, bg="#181818")
        header.pack(fill=tk.X, padx=28, pady=(24, 0))
        tk.Label(header, text="Biblioteca", bg="#181818", fg="white",
                 font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        tk.Label(header, text=f"{len(books)} livro(s)", bg="#181818", fg="#555",
                 font=("Arial", 10)).pack(side=tk.LEFT, padx=12, pady=4)

        if not books:
            self._empty_state(
                "Sua biblioteca está vazia",
                "Clique em '+ Adicionar PDF' para começar"
            )
            return

        self._render_grid(books, mode="library")

    def _show_recent(self):
        self._set_active_sidebar(self._btn_recent)
        self._clear_main()
        recent = load_recent()

        header = tk.Frame(self._main, bg="#181818")
        header.pack(fill=tk.X, padx=28, pady=(24, 0))
        tk.Label(header, text="Recentes", bg="#181818", fg="white",
                 font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        if not recent:
            self._empty_state("Nenhum arquivo recente", "Abra um PDF para começar")
            return

        self._render_grid(recent, mode="recent")

    def _set_active_sidebar(self, active_btn):
        for btn in (self._btn_library, self._btn_recent):
            btn.config(bg="#232323" if btn is active_btn else "#141414")

    def _empty_state(self, title, subtitle):
        frame = tk.Frame(self._main, bg="#181818")
        frame.pack(expand=True)
        tk.Label(frame, text="📚", bg="#181818", fg="#333",
                 font=("Arial", 48)).pack(pady=(0, 12))
        tk.Label(frame, text=title, bg="#181818", fg="#666",
                 font=("Arial", 13, "bold")).pack()
        tk.Label(frame, text=subtitle, bg="#181818", fg="#444",
                 font=("Arial", 10)).pack(pady=(4, 0))

    # ------------------------------------------------------------------ Grid de cards

    def _render_grid(self, items, mode: str):
        # Container scrollável
        outer = tk.Frame(self._main, bg="#181818")
        outer.pack(fill=tk.BOTH, expand=True, padx=12, pady=16)

        canvas = tk.Canvas(outer, bg="#181818", highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        grid_frame = tk.Frame(canvas, bg="#181818")

        grid_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=grid_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))
        grid_frame.bind("<MouseWheel>", lambda e: canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Renderiza cards em thread para não travar a UI
        for i, item in enumerate(items):
            card = self._make_card(grid_frame, item, mode)
            card.grid(row=i // 5, column=i % 5, padx=10, pady=10, sticky=tk.NW)

    def _make_card(self, parent, item: dict, mode: str):
        path = item["path"]
        name = item["name"]
        exists = os.path.exists(path)

        card = tk.Frame(parent, bg="#222222", width=CARD_W, height=CARD_H,
                        cursor="hand2" if exists else "arrow")
        card.pack_propagate(False)

        # Capa
        cover_frame = tk.Frame(card, bg="#2a2a2a", width=THUMB_W, height=THUMB_H)
        cover_frame.pack(padx=10, pady=(10, 6))
        cover_frame.pack_propagate(False)

        # Placeholder enquanto carrega
        placeholder = tk.Label(cover_frame, text="PDF", bg="#333",
                                fg="#555", font=("Arial", 14, "bold"),
                                width=THUMB_W, height=THUMB_H)
        placeholder.pack(fill=tk.BOTH, expand=True)

        if exists:
            threading.Thread(
                target=self._load_thumb,
                args=(path, cover_frame, placeholder),
                daemon=True
            ).start()
        else:
            placeholder.config(text="!\nNão\nencontrado", fg="#c0392b")

        # Nome
        short = name.replace(".pdf", "").replace(".PDF", "")
        short = short if len(short) <= 18 else short[:15] + "..."
        fg = "white" if exists else "#555"
        tk.Label(card, text=short, bg="#222222", fg=fg,
                 font=("Arial", 8, "bold"), wraplength=CARD_W - 10,
                 justify=tk.CENTER).pack(pady=(0, 4))

        # Botão remover (×)
        btn_remove = tk.Label(card, text="×", bg="#222222", fg="#444",
                              font=("Arial", 14), cursor="hand2")
        btn_remove.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-4, y=2)
        btn_remove.bind("<Enter>", lambda e, b=btn_remove: b.config(fg="#ff6b6b"))
        btn_remove.bind("<Leave>", lambda e, b=btn_remove: b.config(fg="#444"))

        if mode == "library":
            btn_remove.bind("<Button-1>", lambda e, p=path: self._remove_library(p))
        else:
            from core.history import remove_recent
            btn_remove.bind("<Button-1>", lambda e, p=path: self._remove_recent(p))

        # Clique para abrir
        if exists:
            for w in (card, cover_frame, placeholder):
                w.bind("<Button-1>", lambda e, p=path: self._on_open(p))
            self._hover(card)

        return card

    def _load_thumb(self, path, cover_frame, placeholder):
        """Roda em thread separada — carrega/gera miniatura e atualiza UI."""
        thumb_path = get_thumbnail(path)
        if not thumb_path:
            return
        try:
            img = Image.open(thumb_path).resize((THUMB_W, THUMB_H), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._thumb_refs.append(photo)

            def update():
                placeholder.config(image=photo, text="", bg="#2a2a2a")
                placeholder.image = photo

            cover_frame.after(0, update)
        except Exception:
            pass

    def _hover(self, card):
        def on_enter(e):
            card.config(bg="#2c2c2c")
            for w in card.winfo_children():
                try: w.config(bg="#2c2c2c")
                except: pass

        def on_leave(e):
            card.config(bg="#222222")
            for w in card.winfo_children():
                try: w.config(bg="#222222")
                except: pass

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    # ------------------------------------------------------------------ Ações

    def add_to_library(self):
        paths = filedialog.askopenfilenames(
            title="Adicionar PDFs à biblioteca",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        for path in paths:
            add_to_library(path)
        if paths:
            self._show_library()

    def _remove_library(self, path):
        remove_from_library(path)
        self._show_library()

    def _remove_recent(self, path):
        from core.history import remove_recent
        remove_recent(path)
        self._show_recent()

    def refresh(self):
        self._show_library()