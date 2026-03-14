import tkinter as tk


class TabBar(tk.Frame):
    """Barra de abas horizontal."""

    def __init__(self, parent, on_select, on_close):
        super().__init__(parent, bg="#141414", height=38)
        self.pack_propagate(False)

        self._on_select = on_select
        self._on_close = on_close
        self._tabs = {}      # tab_id -> dict de widgets
        self._active_id = None

        self._add_home_tab()

    # ------------------------------------------------------------------ Tabs

    def _add_home_tab(self):
        self._add_tab_widget("home", "⌂  Início", closeable=False)
        self.set_active("home")

    def add_tab(self, tab_id: str, title: str):
        self._add_tab_widget(tab_id, title, closeable=True)
        self.set_active(tab_id)

    def _add_tab_widget(self, tab_id: str, title: str, closeable: bool):
        frame = tk.Frame(self, bg="#2a2a2a", padx=14, cursor="hand2")
        frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 1))

        label = tk.Label(frame, text=title, bg="#2a2a2a", fg="#999",
                         font=("Arial", 9), cursor="hand2")
        label.pack(side=tk.LEFT, pady=10)

        widgets = {"frame": frame, "label": label}

        if closeable:
            btn_x = tk.Label(frame, text="×", bg="#2a2a2a", fg="#555",
                             font=("Arial", 12), cursor="hand2", padx=4)
            btn_x.pack(side=tk.LEFT, pady=8)
            btn_x.bind("<Button-1>", lambda e, t=tab_id: self._on_close(t))
            btn_x.bind("<Enter>", lambda e, b=btn_x: b.config(fg="#ff6b6b"))
            btn_x.bind("<Leave>", lambda e, b=btn_x, t=tab_id: b.config(
                fg="white" if self._active_id == t else "#555"))
            widgets["btn_x"] = btn_x

        frame.bind("<Button-1>", lambda e, t=tab_id: self._on_select(t))
        label.bind("<Button-1>", lambda e, t=tab_id: self._on_select(t))

        self._tabs[tab_id] = widgets

    # ------------------------------------------------------------------ Estado

    def set_active(self, tab_id: str):
        for tid, w in self._tabs.items():
            active = tid == tab_id
            bg = "#1e1e1e" if active else "#2a2a2a"
            fg_label = "white" if active else "#999"
            w["frame"].config(bg=bg)
            w["label"].config(bg=bg, fg=fg_label)
            if "btn_x" in w:
                w["btn_x"].config(bg=bg, fg="white" if active else "#555")
        self._active_id = tab_id

    def remove_tab(self, tab_id: str):
        if tab_id in self._tabs:
            self._tabs[tab_id]["frame"].destroy()
            del self._tabs[tab_id]

    def update_title(self, tab_id: str, title: str):
        if tab_id in self._tabs:
            self._tabs[tab_id]["label"].config(text=title)

    def has_tab(self, tab_id: str) -> bool:
        return tab_id in self._tabs