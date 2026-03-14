import tkinter as tk


class Toolbar(tk.Frame):
    """Barra de ferramentas superior com botões de navegação e zoom."""

    def __init__(self, parent, callbacks: dict):
        super().__init__(parent, bg="#2d2d2d", pady=6)

        self._callbacks = callbacks
        self._build()

    def _build(self):
        btn = {"bg": "#3a3a3a", "fg": "white", "relief": "flat",
               "padx": 10, "pady": 4, "cursor": "hand2",
               "activebackground": "#505050", "activeforeground": "white"}

        def sep():
            tk.Frame(self, bg="#555", width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        tk.Button(self, text="Abrir PDF", command=self._callbacks["open"], **btn).pack(side=tk.LEFT, padx=(8, 4))

        sep()

        tk.Button(self, text="◀ Anterior", command=self._callbacks["prev"], **btn).pack(side=tk.LEFT, padx=2)
        tk.Button(self, text="Próxima ▶", command=self._callbacks["next"], **btn).pack(side=tk.LEFT, padx=2)

        sep()

        tk.Label(self, text="Página:", bg="#2d2d2d", fg="#aaa").pack(side=tk.LEFT)
        self.page_entry = tk.Entry(self, width=5, bg="#3a3a3a", fg="white",
                                   insertbackground="white", relief="flat")
        self.page_entry.pack(side=tk.LEFT, padx=(4, 2))
        self.page_entry.bind("<Return>", self._callbacks["go_to"])

        self.total_label = tk.Label(self, text="/ -", bg="#2d2d2d", fg="#aaa")
        self.total_label.pack(side=tk.LEFT)

        sep()

        tk.Button(self, text="Zoom −", command=self._callbacks["zoom_out"],   **btn).pack(side=tk.LEFT, padx=2)
        tk.Button(self, text="Zoom +", command=self._callbacks["zoom_in"],    **btn).pack(side=tk.LEFT, padx=2)
        tk.Button(self, text="100%",   command=self._callbacks["zoom_reset"], **btn).pack(side=tk.LEFT, padx=2)

    def update_page(self, current: int, total: int):
        """Atualiza o campo de página e o total."""
        self.page_entry.delete(0, tk.END)
        self.page_entry.insert(0, str(current))
        self.total_label.config(text=f"/ {total}")

    def get_page_input(self) -> str:
        return self.page_entry.get()
