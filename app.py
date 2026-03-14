import tkinter as tk
from tkinter import filedialog, messagebox

from core.history import add_recent
from core.library import add_to_library
from ui.toolbar import Toolbar
from ui.tabbar import TabBar
from ui.statusbar import Statusbar
from ui.home import HomeScreen
from ui.pdftab import PDFTab


class App:
    """Classe principal — gerencia abas, home e toolbar."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PyReaderPDF")
        self.root.geometry("1100x750")
        self.root.configure(bg="#1e1e1e")

        self._tabs = {}          # tab_id -> PDFTab
        self._active_id = "home"
        self._tab_counter = 0

        self._build_ui()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        callbacks = {
            "open":         self.open_file,
            "prev":         self.prev_page,
            "next":         self.next_page,
            "go_to":        self.go_to_page,
            "zoom_in":      self.zoom_in,
            "zoom_out":     self.zoom_out,
            "zoom_reset":   self.zoom_reset,
            "toggle_split": self.toggle_split,
            "toggle_sync":  self.toggle_sync,
            "add_to_library": self.add_active_to_library,
        }

        self.toolbar = Toolbar(self.root, callbacks)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        self.tabbar = TabBar(self.root,
                             on_select=self._select_tab,
                             on_close=self._close_tab)
        self.tabbar.pack(side=tk.TOP, fill=tk.X)

        self.statusbar = Statusbar(self.root)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.content = tk.Frame(self.root, bg="#1e1e1e")
        self.content.pack(fill=tk.BOTH, expand=True)

        # Home (sempre presente, só oculta)
        self.home = HomeScreen(self.content, on_open=self.open_path)
        self.home.pack(fill=tk.BOTH, expand=True)

        self.toolbar.set_pdf_controls_enabled(False)

    # ------------------------------------------------------------------ Abrir arquivo

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Selecionar PDF",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if path:
            self.open_path(path)

    def open_path(self, path: str):
        # Se já está aberto em alguma aba, só ativa
        for tab_id, tab in self._tabs.items():
            if tab.path == path:
                self._select_tab(tab_id)
                return

        self._tab_counter += 1
        tab_id = f"tab_{self._tab_counter}"
        filename = path.replace("\\", "/").split("/")[-1]
        short = filename if len(filename) <= 20 else filename[:17] + "..."

        tab = PDFTab(self.content, path,
                     on_status_change=lambda c, t, z, tid=tab_id: self._on_status(tid, c, t, z))
        self._tabs[tab_id] = tab

        self.tabbar.add_tab(tab_id, short)
        add_recent(path)
        add_to_library(path)
        self.home.refresh()
        self._select_tab(tab_id)

    # ------------------------------------------------------------------ Gerenciar abas

    def _select_tab(self, tab_id: str):
        # Oculta conteúdo atual
        if self._active_id == "home":
            self.home.pack_forget()
        elif self._active_id in self._tabs:
            self._tabs[self._active_id].pack_forget()

        self._active_id = tab_id
        self.tabbar.set_active(tab_id)

        if tab_id == "home":
            self.home.pack(fill=tk.BOTH, expand=True)
            self.toolbar.set_pdf_controls_enabled(False)
            self.statusbar.set_message("Início")
            self.root.title("PyReaderPDF")
        else:
            tab = self._tabs[tab_id]
            tab.pack(fill=tk.BOTH, expand=True)
            self.toolbar.set_pdf_controls_enabled(True)
            self.toolbar.set_split_active(tab.split_active)
            self.toolbar.set_sync_active(tab.sync_active)
            self.toolbar.update_page(tab.current_page, tab.total_pages)
            self.statusbar.update(tab.current_page, tab.total_pages, tab.doc.zoom)
            self.root.title(f"PyReaderPDF — {tab.filename}")

    def _close_tab(self, tab_id: str):
        if tab_id not in self._tabs:
            return

        self._tabs[tab_id].destroy()
        del self._tabs[tab_id]
        self.tabbar.remove_tab(tab_id)

        if self._active_id == tab_id:
            # Ativa a última aba aberta, ou home
            remaining = list(self._tabs.keys())
            next_id = remaining[-1] if remaining else "home"
            self._active_id = None
            self._select_tab(next_id)

    def _active_tab(self):
        """Retorna o PDFTab ativo, ou None se for home."""
        if self._active_id in self._tabs:
            return self._tabs[self._active_id]
        return None

    def _on_status(self, tab_id: str, current: int, total: int, zoom: float):
        if tab_id == self._active_id:
            self.toolbar.update_page(current, total)
            self.statusbar.update(current, total, zoom)

    # ------------------------------------------------------------------ Ações da toolbar

    def next_page(self):
        tab = self._active_tab()
        if tab:
            tab.next_page()

    def prev_page(self):
        tab = self._active_tab()
        if tab:
            tab.prev_page()

    def go_to_page(self, event=None):
        tab = self._active_tab()
        if not tab:
            return
        try:
            page = int(self.toolbar.get_page_input())
            if not tab.go_to(page):
                messagebox.showwarning("Aviso", f"Página inválida. Total: {tab.total_pages}")
        except ValueError:
            messagebox.showwarning("Aviso", "Digite um número de página válido.")

    def zoom_in(self):
        tab = self._active_tab()
        if tab:
            tab.zoom_in()

    def zoom_out(self):
        tab = self._active_tab()
        if tab:
            tab.zoom_out()

    def zoom_reset(self):
        tab = self._active_tab()
        if tab:
            tab.zoom_reset()

    def toggle_split(self):
        tab = self._active_tab()
        if not tab:
            return
        active = tab.toggle_split()
        self.toolbar.set_split_active(active)
        msg = "Split View ativo" if active else "Split View desativado"
        self.statusbar.set_message(msg)

    def toggle_sync(self):
        tab = self._active_tab()
        if not tab:
            return
        active = tab.toggle_sync()
        self.toolbar.set_sync_active(active)
        msg = "Scroll sincronizado ativado" if active else "Scroll sincronizado desativado"
        self.statusbar.set_message(msg)

    def add_active_to_library(self):
        tab = self._active_tab()
        if not tab:
            return
        add_to_library(tab.path)
        self.home.refresh()
        self.statusbar.set_message(f"'{tab.filename}' adicionado à biblioteca")