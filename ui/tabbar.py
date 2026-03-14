import tkinter as tk


class TabBar(tk.Frame):
    """Barra de abas com suporte a drag para criar split view."""

    def __init__(self, parent, on_select, on_close, on_drag_move=None, on_drag_end=None):
        super().__init__(parent, bg="#141414", height=38)
        self.pack_propagate(False)

        self._on_select   = on_select
        self._on_close    = on_close
        self._on_drag_move = on_drag_move  # (tab_id, x_root, y_root)
        self._on_drag_end  = on_drag_end   # (tab_id, x_root, y_root)

        self._tabs        = {}
        self._active_id   = None

        # Estado do drag
        self._drag_id     = None
        self._drag_ghost  = None
        self._drag_active = False

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
            btn_x.bind("<Button-1>",  lambda e, t=tab_id: self._on_close(t))
            btn_x.bind("<Enter>",     lambda e, b=btn_x: b.config(fg="#ff6b6b"))
            btn_x.bind("<Leave>",     lambda e, b=btn_x, t=tab_id: b.config(
                fg="white" if self._active_id == t else "#555"))
            widgets["btn_x"] = btn_x

        # Clique simples → seleciona
        for w in (frame, label):
            w.bind("<Button-1>",        lambda e, t=tab_id: self._on_press(e, t))
            w.bind("<B1-Motion>",       lambda e, t=tab_id: self._on_motion(e, t))
            w.bind("<ButtonRelease-1>", lambda e, t=tab_id: self._on_release(e, t))

        self._tabs[tab_id] = widgets

    # ------------------------------------------------------------------ Drag

    def _on_press(self, event, tab_id):
        self._drag_id     = tab_id
        self._drag_active = False
        self._drag_start_y = event.y_root

    def _on_motion(self, event, tab_id):
        if self._drag_id != tab_id:
            return

        # Só ativa drag se arrastar >25px para baixo
        if not self._drag_active:
            if event.y_root - self._drag_start_y > 25:
                self._drag_active = True
                self._create_ghost(tab_id)
        
        if self._drag_active:
            if self._drag_ghost:
                self._drag_ghost.geometry(
                    f"+{event.x_root - 60}+{event.y_root - 15}")
            if self._on_drag_move:
                self._on_drag_move(tab_id, event.x_root, event.y_root)

    def _on_release(self, event, tab_id):
        self._destroy_ghost()

        if self._drag_active:
            self._drag_active = False
            if self._on_drag_end:
                self._on_drag_end(tab_id, event.x_root, event.y_root)
        else:
            # Clique normal
            self._on_select(tab_id)

        self._drag_id = None

    def _create_ghost(self, tab_id: str):
        name = self._tabs[tab_id]["label"].cget("text") if tab_id in self._tabs else tab_id
        self._drag_ghost = tk.Toplevel()
        self._drag_ghost.overrideredirect(True)
        self._drag_ghost.attributes("-alpha", 0.75)
        self._drag_ghost.configure(bg="#3a3a3a")
        tk.Label(self._drag_ghost, text=f"  {name}  ", bg="#3a3a3a",
                 fg="white", font=("Arial", 9), pady=6).pack()

    def _destroy_ghost(self):
        if self._drag_ghost:
            try:
                self._drag_ghost.destroy()
            except Exception:
                pass
            self._drag_ghost = None

    # ------------------------------------------------------------------ Estado

    def set_active(self, tab_id: str):
        for tid, w in self._tabs.items():
            active = tid == tab_id
            bg = "#1e1e1e" if active else "#2a2a2a"
            w["frame"].config(bg=bg)
            w["label"].config(bg=bg, fg="white" if active else "#999")
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