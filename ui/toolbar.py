import tkinter as tk


class Toolbar(tk.Frame):
    """Barra de ferramentas principal."""

    def __init__(self, parent, callbacks: dict):
        super().__init__(parent, bg="#2d2d2d", pady=6)
        self._callbacks = callbacks
        self._pdf_widgets = []  # widgets desabilitados na home
        self._build()

    def _build(self):
        btn = {"bg": "#3a3a3a", "fg": "white", "relief": "flat",
               "padx": 10, "pady": 4, "cursor": "hand2",
               "activebackground": "#505050", "activeforeground": "white"}

        def sep():
            tk.Frame(self, bg="#555", width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        tk.Button(self, text="Abrir PDF", command=self._callbacks["open"],
                  **btn).pack(side=tk.LEFT, padx=(8, 4))

        sep()

        self.btn_prev = tk.Button(self, text="◀ Anterior",
                                  command=self._callbacks["prev"], **btn)
        self.btn_prev.pack(side=tk.LEFT, padx=2)

        self.btn_next = tk.Button(self, text="Próxima ▶",
                                  command=self._callbacks["next"], **btn)
        self.btn_next.pack(side=tk.LEFT, padx=2)

        sep()

        tk.Label(self, text="Página:", bg="#2d2d2d", fg="#aaa").pack(side=tk.LEFT)
        self.page_entry = tk.Entry(self, width=5, bg="#3a3a3a", fg="white",
                                   insertbackground="white", relief="flat")
        self.page_entry.pack(side=tk.LEFT, padx=(4, 2))
        self.page_entry.bind("<Return>", self._callbacks["go_to"])

        self.total_label = tk.Label(self, text="/ -", bg="#2d2d2d", fg="#aaa")
        self.total_label.pack(side=tk.LEFT)

        sep()

        self.btn_zoom_out = tk.Button(self, text="Zoom −",
                                      command=self._callbacks["zoom_out"], **btn)
        self.btn_zoom_out.pack(side=tk.LEFT, padx=2)

        self.btn_zoom_in = tk.Button(self, text="Zoom +",
                                     command=self._callbacks["zoom_in"], **btn)
        self.btn_zoom_in.pack(side=tk.LEFT, padx=2)

        self.btn_zoom_reset = tk.Button(self, text="100%",
                                        command=self._callbacks["zoom_reset"], **btn)
        self.btn_zoom_reset.pack(side=tk.LEFT, padx=2)

        sep()

        self.btn_split = tk.Button(self, text="⊞ Split View",
                                   command=self._callbacks["toggle_split"], **btn)
        self.btn_split.pack(side=tk.LEFT, padx=2)

        self.btn_sync = tk.Button(self, text="⇅ Sincronizar",
                                  command=self._callbacks["toggle_sync"],
                                  state=tk.DISABLED, **btn)
        self.btn_sync.pack(side=tk.LEFT, padx=2)

        tk.Frame(self, bg="#555", width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        self.btn_add_lib = tk.Button(self, text="+ Biblioteca",
                                     command=self._callbacks.get("add_to_library", lambda: None),
                                     **btn)
        self.btn_add_lib.pack(side=tk.LEFT, padx=2)

        self._pdf_widgets = [
            self.btn_prev, self.btn_next, self.page_entry,
            self.btn_zoom_in, self.btn_zoom_out, self.btn_zoom_reset,
            self.btn_split, self.btn_sync, self.btn_add_lib,
        ]

    # ------------------------------------------------------------------ Estado

    def set_pdf_controls_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        fg = "white" if enabled else "#555"
        for w in self._pdf_widgets:
            try:
                w.config(state=state, fg=fg)
            except Exception:
                pass
        if not enabled:
            self.total_label.config(text="/ -")
            self.page_entry.delete(0, tk.END)

    def set_split_active(self, active: bool):
        if active:
            self.btn_split.config(bg="#1a6b3c", activebackground="#1f8048",
                                  text="⊞ Split View ✓")
            self.btn_sync.config(state=tk.NORMAL, fg="white")
        else:
            self.btn_split.config(bg="#3a3a3a", activebackground="#505050",
                                  text="⊞ Split View")
            self.btn_sync.config(state=tk.DISABLED, bg="#3a3a3a",
                                 text="⇅ Sincronizar", fg="#555")

    def set_sync_active(self, active: bool):
        if active:
            self.btn_sync.config(bg="#1a4f6b", activebackground="#1f6080",
                                 text="⇅ Sincronizar ✓")
        else:
            self.btn_sync.config(bg="#3a3a3a", activebackground="#505050",
                                 text="⇅ Sincronizar")

    def update_page(self, current: int, total: int):
        self.page_entry.delete(0, tk.END)
        self.page_entry.insert(0, str(current))
        self.total_label.config(text=f"/ {total}")

    def get_page_input(self) -> str:
        return self.page_entry.get()