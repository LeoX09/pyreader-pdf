import tkinter as tk

from ui.panel import Panel


class SplitView(tk.Frame):
    """Divide a tela em dois painéis independentes separados por um divisor arrastável."""

    def __init__(self, parent, on_status_change=None):
        super().__init__(parent, bg="#1e1e1e")

        self.on_status_change = on_status_change
        self._sync_enabled = False

        self._build()

    # ------------------------------------------------------------------ UI

    def _build(self):
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                                    bg="#444", sashwidth=5,
                                    sashrelief="flat", handlesize=0)
        self.paned.pack(fill=tk.BOTH, expand=True)

        self.panel_a = Panel(self.paned, panel_id="A",
                             on_status_change=self.on_status_change)
        self.panel_b = Panel(self.paned, panel_id="B",
                             on_status_change=self.on_status_change)

        self.paned.add(self.panel_a, stretch="always", minsize=200)
        self.paned.add(self.panel_b, stretch="always", minsize=200)

        self._setup_sync()

    def _setup_sync(self):
        """Conecta os callbacks de scroll sincronizado entre os painéis."""
        def sync_a_to_b(delta):
            if self._sync_enabled:
                self.panel_b.scroll_to(delta)

        def sync_b_to_a(delta):
            if self._sync_enabled:
                self.panel_a.scroll_to(delta)

        self.panel_a.sync_callback = sync_a_to_b
        self.panel_b.sync_callback = sync_b_to_a

    # ------------------------------------------------------------------ Controles

    def set_sync_scroll(self, enabled: bool):
        """Ativa ou desativa a sincronização de scroll entre os painéis."""
        self._sync_enabled = enabled
        self.panel_a.sync_scroll = enabled
        self.panel_b.sync_scroll = enabled

    def open_in_both(self, path: str):
        """Abre o mesmo arquivo nos dois painéis (atalho útil)."""
        self.panel_a.open_path(path)
        self.panel_b.open_path(path)
