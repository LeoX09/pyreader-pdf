import tkinter as tk
from tkinter import filedialog, messagebox

from core.history import add_recent
from core.library import add_to_library
from ui.toolbar import Toolbar
from ui.tabbar import TabBar
from ui.statusbar import Statusbar
from ui.home import HomeScreen
from ui.pdftab import PDFTab, MODE_SINGLE, MODE_CONTINUOUS


class App:
    """Classe principal — gerencia abas, home, split view e atalhos."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PyReaderPDF")
        self.root.geometry("1100x750")
        self.root.configure(bg="#1e1e1e")

        self._tabs         = {}       # tab_id -> PDFTab
        self._active_id    = "home"
        self._tab_counter  = 0

        # Split view
        self._is_split       = False
        self._split_paned    = None
        self._split_left_id  = None
        self._split_right_id = None
        self._split_left_view  = None
        self._split_right_view = None
        self._focused_split  = "left"   # qual painel tem foco

        # Drop zones (overlays visíveis durante drag)
        self._drop_left  = None
        self._drop_right = None

        self._build_ui()
        self._bind_shortcuts()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        callbacks = {
            "open":             self.open_file,
            "prev":             self.prev_page,
            "next":             self.next_page,
            "go_to":            self.go_to_page,
            "zoom_in":          self.zoom_in,
            "zoom_out":         self.zoom_out,
            "zoom_reset":       self.zoom_reset,
            "toggle_view_mode": self.toggle_view_mode,
            "add_to_library":   self.add_active_to_library,
        }

        self.toolbar = Toolbar(self.root, callbacks)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        self.tabbar = TabBar(
            self.root,
            on_select=self._select_tab,
            on_close=self._close_tab,
            on_drag_move=self._on_tab_drag_move,
            on_drag_end=self._on_tab_drag_end,
        )
        self.tabbar.pack(side=tk.TOP, fill=tk.X)

        self.statusbar = Statusbar(self.root)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.content = tk.Frame(self.root, bg="#1e1e1e")
        self.content.pack(fill=tk.BOTH, expand=True)

        self.home = HomeScreen(self.content, on_open=self.open_path)
        self.home.pack(fill=tk.BOTH, expand=True)

        self.toolbar.set_pdf_controls_enabled(False)

    def _bind_shortcuts(self):
        self.root.bind("<Control-d>", lambda e: self.duplicate_tab())
        self.root.bind("<Control-D>", lambda e: self.duplicate_tab())
        self.root.bind("<Control-w>", lambda e: self.close_split())
        self.root.bind("<Control-W>", lambda e: self.close_split())
        self.root.bind("<Escape>",    lambda e: self.close_split())

    # ------------------------------------------------------------------ Abrir arquivo

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Selecionar PDF",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if path:
            self.open_path(path)

    def open_path(self, path: str):
        # Se já está aberto, só ativa
        for tab_id, tab in self._tabs.items():
            if tab.path == path:
                self._select_tab(tab_id)
                return

        self._tab_counter += 1
        tab_id   = f"tab_{self._tab_counter}"
        filename = path.replace("\\", "/").split("/")[-1]
        short    = filename if len(filename) <= 22 else filename[:19] + "..."

        tab = PDFTab(
            self.content, path,
            on_status_change=lambda c, t, z, tid=tab_id: self._on_status(tid, c, t, z)
        )
        self._tabs[tab_id] = tab

        self.tabbar.add_tab(tab_id, short)
        add_recent(path)
        add_to_library(path)
        self.home.refresh()
        self._select_tab(tab_id)

    # ------------------------------------------------------------------ Duplicar aba

    def duplicate_tab(self):
        """Ctrl+D — abre uma segunda aba do mesmo arquivo."""
        tab = self._active_tab()
        if not tab:
            return

        self._tab_counter += 1
        tab_id   = f"tab_{self._tab_counter}"
        filename = tab.filename
        short    = filename if len(filename) <= 22 else filename[:19] + "..."
        short    = f"{short} (2)"

        new_tab = PDFTab(
            self.content, tab.path,
            on_status_change=lambda c, t, z, tid=tab_id: self._on_status(tid, c, t, z)
        )
        self._tabs[tab_id] = new_tab
        self.tabbar.add_tab(tab_id, short)
        self._select_tab(tab_id)

        self.statusbar.set_message(
            "Aba duplicada — arraste-a para baixo para criar Split View")

    # ------------------------------------------------------------------ Gerenciar abas

    def _select_tab(self, tab_id: str):
        if self._is_split:
            self.close_split()

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
            self.toolbar.set_view_mode(tab.view_mode)
            self.toolbar.update_page(tab.current_page, tab.total_pages)
            self.statusbar.update(tab.current_page, tab.total_pages, tab.doc.zoom)
            self.root.title(f"PyReaderPDF — {tab.filename}")

    def _close_tab(self, tab_id: str):
        if tab_id not in self._tabs:
            return
        if self._is_split and tab_id in (self._split_left_id, self._split_right_id):
            self.close_split()

        self._tabs[tab_id].destroy()
        del self._tabs[tab_id]
        self.tabbar.remove_tab(tab_id)

        if self._active_id == tab_id:
            remaining = list(self._tabs.keys())
            self._active_id = None
            self._select_tab(remaining[-1] if remaining else "home")

    def _active_tab(self) -> PDFTab | None:
        """Retorna o PDFTab com foco — painel focado no split, ou aba ativa normal."""
        if self._is_split:
            return self._focused_split_view()
        if self._active_id in self._tabs:
            return self._tabs[self._active_id]
        return None

    def _focused_split_view(self):
        """Retorna o PDFTab do painel focado no split."""
        if self._focused_split == "left":
            return self._split_left_view
        return self._split_right_view

    def _set_split_focus(self, side: str):
        """Define qual painel do split tem foco e atualiza toolbar."""
        self._focused_split = side
        view = self._focused_split_view()
        if view and view.doc.is_open:
            self.toolbar.update_page(view.current_page, view.total_pages)
            self.toolbar.set_view_mode(view.view_mode)
            self.statusbar.update(view.current_page, view.total_pages, view.doc.zoom)
        self._update_split_focus_indicator()

    def _update_split_focus_indicator(self):
        """Destaca visualmente o painel focado com borda colorida."""
        if not self._is_split:
            return
        for side, view in (("left", self._split_left_view), ("right", self._split_right_view)):
            if view:
                color = "#2980b9" if side == self._focused_split else "#1e1e1e"
                view.config(highlightbackground=color, highlightthickness=2)

    def _on_status(self, tab_id: str, current: int, total: int, zoom: float):
        if tab_id == self._active_id and not self._is_split:
            self.toolbar.update_page(current, total)
            self.statusbar.update(current, total, zoom)

    # ------------------------------------------------------------------ Split View (drag)

    def _on_tab_drag_move(self, tab_id: str, x_root: int, y_root: int):
        """Mostra zonas de drop enquanto arrasta."""
        # Só mostra se arrastar para a área de conteúdo
        content_top = self.content.winfo_rooty()
        if y_root < content_top:
            self._hide_drop_zones()
            return
        self._show_drop_zones(x_root)

    def _on_tab_drag_end(self, tab_id: str, x_root: int, y_root: int):
        """Verifica se soltou sobre uma zona de drop."""
        self._hide_drop_zones()

        content_top = self.content.winfo_rooty()
        if y_root < content_top:
            return  # soltou na tabbar — ignora

        # Determina lado: esquerda ou direita
        content_cx = self.content.winfo_rootx() + self.content.winfo_width() // 2
        side = "left" if x_root < content_cx else "right"

        # Busca a aba "outra" — qualquer aba aberta que não seja a arrastada
        other_id = None
        # Preferência: aba que estava ativa antes
        if self._active_id != tab_id and self._active_id in self._tabs:
            other_id = self._active_id
        else:
            # Pega qualquer outra aba disponível
            for tid in self._tabs:
                if tid != tab_id:
                    other_id = tid
                    break

        if other_id is None:
            self._select_tab(tab_id)
            return

        if side == "left":
            self._enter_split(left_id=tab_id, right_id=other_id)
        else:
            self._enter_split(left_id=other_id, right_id=tab_id)

    def _show_drop_zones(self, x_root: int):
        if self._drop_left and self._drop_right:
            return  # já visíveis

        w = self.content.winfo_width()
        h = self.content.winfo_height()
        cx = self.content.winfo_rootx() + w // 2

        # Zona esquerda
        self._drop_left = tk.Frame(self.content, bg="#1a3a2a")
        self._drop_left.place(x=0, y=0, relwidth=0.5, relheight=1)
        tk.Label(self._drop_left, text="◧  Esquerda", bg="#1a3a2a",
                 fg="#2ecc71", font=("Arial", 14, "bold")).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Zona direita
        self._drop_right = tk.Frame(self.content, bg="#1a2a3a")
        self._drop_right.place(relx=0.5, y=0, relwidth=0.5, relheight=1)
        tk.Label(self._drop_right, text="◨  Direita", bg="#1a2a3a",
                 fg="#3498db", font=("Arial", 14, "bold")).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Destaca a zona onde o cursor está
        is_left = x_root < cx
        self._drop_left.config( bg="#1f5c38" if is_left  else "#1a3a2a")
        self._drop_right.config(bg="#1a2a3a" if is_left  else "#1f4060")

    def _hide_drop_zones(self):
        for z in (self._drop_left, self._drop_right):
            if z:
                try:
                    z.destroy()
                except Exception:
                    pass
        self._drop_left  = None
        self._drop_right = None

    def _enter_split(self, left_id: str, right_id: str):
        """Ativa o split view com dois tabs lado a lado."""
        if left_id not in self._tabs or right_id not in self._tabs:
            return

        # Oculta a visualização atual
        if self._active_id == "home":
            self.home.pack_forget()
        elif self._active_id in self._tabs:
            self._tabs[self._active_id].pack_forget()

        # PanedWindow de split
        self._split_paned = tk.PanedWindow(
            self.content, orient=tk.HORIZONTAL,
            bg="#2a2a2a", sashwidth=6, sashrelief="flat",
            handlesize=0,
        )
        self._split_paned.pack(fill=tk.BOTH, expand=True)

        left_frame  = tk.Frame(self._split_paned, bg="#1e1e1e")
        right_frame = tk.Frame(self._split_paned, bg="#1e1e1e")
        self._split_paned.add(left_frame,  stretch="always", minsize=280)
        self._split_paned.add(right_frame, stretch="always", minsize=280)

        # Cria views independentes para o split (não pode reparentar widgets tkinter)
        left_path  = self._tabs[left_id].path
        right_path = self._tabs[right_id].path

        self._split_left_view  = PDFTab(left_frame,  left_path)
        self._split_right_view = PDFTab(right_frame, right_path)
        self._split_left_view.pack( fill=tk.BOTH, expand=True)
        self._split_right_view.pack(fill=tk.BOTH, expand=True)

        # Sincroniza página inicial com a aba de origem
        left_page  = self._tabs[left_id].current_page
        right_page = self._tabs[right_id].current_page
        self._split_left_view.go_to(left_page)
        self._split_right_view.go_to(right_page)

        self._is_split       = True
        self._split_left_id  = left_id
        self._split_right_id = right_id
        self._focused_split  = "left"

        # Foco por clique — indica qual painel está ativo
        self._split_left_view.bind( "<Button-1>", lambda e: self._set_split_focus("left"),  add=True)
        self._split_right_view.bind("<Button-1>", lambda e: self._set_split_focus("right"), add=True)
        for child in self._split_left_view.winfo_children():
            child.bind("<Button-1>", lambda e: self._set_split_focus("left"),  add=True)
        for child in self._split_right_view.winfo_children():
            child.bind("<Button-1>", lambda e: self._set_split_focus("right"), add=True)

        self.tabbar.set_active(left_id)
        self.toolbar.set_pdf_controls_enabled(True)
        self._update_split_focus_indicator()
        self.statusbar.set_message(
            "Split View ativo  |  Clique num painel para focar  |  Ctrl+W ou Esc para fechar")
        self.root.title("PyReaderPDF — Split View")

        self._split_paned.bind("<Double-Button-1>", lambda e: self.close_split())

    def close_split(self):
        """Fecha o split view e volta para a aba ativa."""
        if not self._is_split:
            return

        if self._split_left_view:
            self._split_left_view.destroy()
        if self._split_right_view:
            self._split_right_view.destroy()
        if self._split_paned:
            self._split_paned.destroy()

        self._split_paned      = None
        self._split_left_view  = None
        self._split_right_view = None
        self._is_split         = False

        # Volta para a aba que estava ativa antes do split
        prev = self._split_left_id or self._active_id
        self._active_id = None
        self._select_tab(prev if prev in self._tabs else "home")

    # ------------------------------------------------------------------ Ações toolbar

    def next_page(self):
        tab = self._active_tab()
        if tab: tab.next_page()

    def prev_page(self):
        tab = self._active_tab()
        if tab: tab.prev_page()

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
        if tab: tab.zoom_in()

    def zoom_out(self):
        tab = self._active_tab()
        if tab: tab.zoom_out()

    def zoom_reset(self):
        tab = self._active_tab()
        if tab: tab.zoom_reset()

    def toggle_view_mode(self):
        tab = self._active_tab()
        if not tab:
            return
        new_mode = MODE_CONTINUOUS if tab.view_mode == MODE_SINGLE else MODE_SINGLE
        tab.set_view_mode(new_mode)
        self.toolbar.set_view_mode(new_mode)
        panel = f"Painel {self._focused_split.capitalize()} — " if self._is_split else ""
        label = f"{panel}Modo contínuo ativado" if new_mode == MODE_CONTINUOUS else f"{panel}Modo página única ativado"
        self.statusbar.set_message(label)

    def add_active_to_library(self):
        tab = self._active_tab()
        if not tab:
            return
        add_to_library(tab.path)
        self.home.refresh()
        self.statusbar.set_message(f"'{tab.filename}' adicionado à biblioteca")