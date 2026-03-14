import tkinter as tk
import os

from core.history import load_recent, remove_recent


class HomeScreen(tk.Frame):
    """Tela inicial com arquivos recentes."""

    def __init__(self, parent, on_open):
        super().__init__(parent, bg="#1e1e1e")
        self._on_open = on_open
        self._build()

    def _build(self):
        # Cabeçalho
        header = tk.Frame(self, bg="#1e1e1e")
        header.pack(fill=tk.X, padx=40, pady=(40, 0))

        tk.Label(header, text="PyReaderPDF", bg="#1e1e1e", fg="white",
                 font=("Arial", 22, "bold")).pack(side=tk.LEFT)

        tk.Label(self, text="Arquivos recentes", bg="#1e1e1e", fg="#666",
                 font=("Arial", 11)).pack(anchor=tk.W, padx=40, pady=(24, 16))

        # Área scrollável
        container = tk.Frame(self, bg="#1e1e1e")
        container.pack(fill=tk.BOTH, expand=True, padx=40)

        canvas = tk.Canvas(container, bg="#1e1e1e", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        self._scroll_frame = tk.Frame(canvas, bg="#1e1e1e")

        self._scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=self._scroll_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh()

    def refresh(self):
        """Recarrega a lista de recentes."""
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()

        recent = load_recent()

        if not recent:
            tk.Label(self._scroll_frame,
                     text="Nenhum arquivo aberto ainda.\nUse o botão 'Abrir PDF' para começar.",
                     bg="#1e1e1e", fg="#555", font=("Arial", 11),
                     justify=tk.CENTER).pack(pady=60)
            return

        # Grid de cards — 3 por linha
        row_frame = None
        for i, item in enumerate(recent):
            if i % 3 == 0:
                row_frame = tk.Frame(self._scroll_frame, bg="#1e1e1e")
                row_frame.pack(fill=tk.X, pady=6)

            self._make_card(row_frame, item)

    def _make_card(self, parent, item: dict):
        path = item["path"]
        name = item["name"]
        last = item.get("last_opened", "")
        exists = os.path.exists(path)

        card = tk.Frame(parent, bg="#2a2a2a", padx=16, pady=14,
                        cursor="hand2" if exists else "arrow",
                        width=220)
        card.pack(side=tk.LEFT, padx=(0, 12))
        card.pack_propagate(False)

        # Ícone PDF
        icon_color = "#e74c3c" if exists else "#555"
        tk.Label(card, text="PDF", bg=icon_color, fg="white",
                 font=("Arial", 8, "bold"), padx=6, pady=2).pack(anchor=tk.W)

        # Nome do arquivo (truncado)
        display_name = name if len(name) <= 26 else name[:23] + "..."
        fg_name = "white" if exists else "#555"
        tk.Label(card, text=display_name, bg="#2a2a2a", fg=fg_name,
                 font=("Arial", 9, "bold"), wraplength=190,
                 justify=tk.LEFT).pack(anchor=tk.W, pady=(8, 2))

        # Data de abertura
        tk.Label(card, text=last, bg="#2a2a2a", fg="#555",
                 font=("Arial", 8)).pack(anchor=tk.W)

        if not exists:
            tk.Label(card, text="Arquivo não encontrado", bg="#2a2a2a",
                     fg="#c0392b", font=("Arial", 7)).pack(anchor=tk.W, pady=(4, 0))

        # Botão remover
        btn_remove = tk.Label(card, text="×", bg="#2a2a2a", fg="#444",
                              font=("Arial", 13), cursor="hand2")
        btn_remove.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-4, y=4)
        btn_remove.bind("<Button-1>", lambda e, p=path: self._remove(p))
        btn_remove.bind("<Enter>", lambda e, b=btn_remove: b.config(fg="#ff6b6b"))
        btn_remove.bind("<Leave>", lambda e, b=btn_remove: b.config(fg="#444"))

        if exists:
            for widget in (card, *card.winfo_children()):
                widget.bind("<Button-1>", lambda e, p=path: self._on_open(p))
            self._add_hover(card)

    def _add_hover(self, card: tk.Frame):
        def on_enter(e):
            card.config(bg="#333333")
            for w in card.winfo_children():
                try:
                    w.config(bg="#333333")
                except Exception:
                    pass

        def on_leave(e):
            card.config(bg="#2a2a2a")
            for w in card.winfo_children():
                try:
                    w.config(bg="#2a2a2a")
                except Exception:
                    pass

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    def _remove(self, path: str):
        remove_recent(path)
        self.refresh()