import os
import threading

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QPixmap, QImage

from core.library import load_library, add_to_library, remove_from_library
from core.history import load_recent, remove_recent
from core.thumbnail import get_thumbnail

CARD_W = 170
CARD_H = 280
THUMB_W = 150
THUMB_H = 210


class ThumbLoader(QObject):
    """Carrega miniaturas em thread separada."""
    loaded = Signal(int, str, QPixmap)  # index, path, pixmap

    def __init__(self, items):
        super().__init__()
        self._items = items

    def run(self):
        for i, item in enumerate(self._items):
            path = item["path"]
            thumb = get_thumbnail(path)
            if thumb and os.path.exists(thumb):
                img = QImage(thumb).scaled(
                    THUMB_W, THUMB_H,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.loaded.emit(i, path, QPixmap.fromImage(img))


class HomeScreen(QWidget):
    """Tela inicial com biblioteca e recentes."""

    open_requested = Signal(str)
    _thumb_ready   = Signal(str, QPixmap)   # path, pixmap — sinal interno thread-safe

    def __init__(self, parent=None):
        super().__init__(parent)
        self._card_map = {}   # path -> card widget (para atualizar thumb)
        self._mode = "library"
        self._thumb_ready.connect(self._apply_thumb)
        self._build()

    # ------------------------------------------------------------------ Layout

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = self._build_sidebar()
        root.addWidget(sidebar)

        # Divisor
        div = QFrame()
        div.setFixedWidth(1)
        div.setStyleSheet("background:#2a2a2a;")
        root.addWidget(div)

        # Área principal
        self._main_area = QWidget()
        self._main_layout = QVBoxLayout(self._main_area)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._main_area, stretch=1)

        self._show_library()

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background:#141414;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo
        logo = QLabel("PyReaderPDF")
        logo.setStyleSheet("color:white; font-size:13pt; font-weight:bold; padding:20px;")
        layout.addWidget(logo)

        # Divisor
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#2a2a2a; margin:0 16px;")
        layout.addWidget(sep)

        layout.addSpacing(8)

        self._btn_library = self._sidebar_btn("⊟  Biblioteca", self._show_library)
        self._btn_recent  = self._sidebar_btn("⊙  Recentes",   self._show_recent)
        layout.addWidget(self._btn_library)
        layout.addWidget(self._btn_recent)

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background:#2a2a2a; margin:16px;")
        layout.addWidget(sep2)

        btn_add = self._sidebar_btn("＋  Adicionar PDF", self.add_to_library, accent=True)
        layout.addWidget(btn_add)

        layout.addStretch()
        return sidebar

    def _sidebar_btn(self, text, slot, accent=False):
        btn = QPushButton(text)
        btn.setFlat(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(40)
        bg      = "#1a6b3c" if accent else "transparent"
        bg_h    = "#1f8048" if accent else "#232323"
        btn.setStyleSheet(f"""
            QPushButton {{
                color: white; text-align: left;
                padding-left: 20px; font-size: 10pt;
                background: {bg}; border: none;
            }}
            QPushButton:hover {{ background: {bg_h}; }}
        """)
        btn.clicked.connect(slot)
        return btn

    # ------------------------------------------------------------------ Seções

    def _clear_main(self):
        while self._main_layout.count():
            item = self._main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._card_map.clear()

    def _show_library(self):
        self._mode = "library"
        self._set_sidebar_active(self._btn_library)
        self._clear_main()
        items = load_library()
        self._render_section("Biblioteca", items, mode="library")

    def _show_recent(self):
        self._mode = "recent"
        self._set_sidebar_active(self._btn_recent)
        self._clear_main()
        items = load_recent()
        self._render_section("Recentes", items, mode="recent")

    def _set_sidebar_active(self, active):
        for btn in (self._btn_library, self._btn_recent):
            btn.setStyleSheet(btn.styleSheet().replace(
                "background: #232323" if btn is active else "background: transparent",
                ""
            ))
            is_active = btn is active
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: white; text-align: left;
                    padding-left: 20px; font-size: 10pt;
                    background: {"#232323" if is_active else "transparent"};
                    border: none;
                    {"border-left: 3px solid #2980b9;" if is_active else ""}
                }}
                QPushButton:hover {{ background: #232323; }}
            """)

    # ------------------------------------------------------------------ Grid

    def _render_section(self, title: str, items: list, mode: str):
        # Cabeçalho
        header = QWidget()
        header.setStyleSheet("background:#181818;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(28, 20, 28, 12)

        lbl = QLabel(title)
        lbl.setStyleSheet("color:white; font-size:16pt; font-weight:bold; background:transparent;")
        hl.addWidget(lbl)

        count = QLabel(f"  {len(items)} item(s)")
        count.setStyleSheet("color:#555; font-size:9pt; background:transparent;")
        hl.addWidget(count)
        hl.addStretch()
        self._main_layout.addWidget(header)

        if not items:
            self._main_layout.addWidget(self._empty_state())
            return

        # Scroll area com grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:#181818; }")

        container = QWidget()
        container.setStyleSheet("background:#181818;")
        grid = QGridLayout(container)
        grid.setContentsMargins(20, 8, 20, 20)
        grid.setSpacing(14)

        cols = 5
        for i, item in enumerate(items):
            card = self._make_card(item, mode)
            grid.addWidget(card, i // cols, i % cols)
            self._card_map[item["path"]] = card

        # Preenche colunas restantes
        remainder = len(items) % cols
        if remainder:
            for j in range(cols - remainder):
                spacer = QWidget()
                spacer.setFixedSize(CARD_W, CARD_H)
                grid.addWidget(spacer, len(items) // cols, remainder + j)

        grid.setRowStretch(grid.rowCount(), 1)
        scroll.setWidget(container)
        self._main_layout.addWidget(scroll, stretch=1)

        # Carrega miniaturas em background
        self._load_thumbs(items)

    def _empty_state(self):
        w = QWidget()
        w.setStyleSheet("background:#181818;")
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        icon = QLabel("📚")
        icon.setStyleSheet("font-size:48pt; background:transparent;")
        icon.setAlignment(Qt.AlignCenter)
        msg = QLabel("Nenhum item ainda\nUse '+ Adicionar PDF' para começar")
        msg.setStyleSheet("color:#555; font-size:11pt; background:transparent;")
        msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        layout.addWidget(msg)
        return w

    # ------------------------------------------------------------------ Card

    def _make_card(self, item: dict, mode: str) -> QWidget:
        path   = item["path"]
        name   = item["name"].replace(".pdf", "").replace(".PDF", "")
        exists = os.path.exists(path)
        short  = name if len(name) <= 18 else name[:15] + "..."

        card = QFrame()
        card.setFixedSize(CARD_W, CARD_H)
        card.setStyleSheet("""
            QFrame { background:#222; border-radius:6px; }
            QFrame:hover { background:#2c2c2c; }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(6)

        # Thumb
        thumb_lbl = QLabel()
        thumb_lbl.setFixedSize(THUMB_W, THUMB_H)
        thumb_lbl.setAlignment(Qt.AlignCenter)
        thumb_lbl.setStyleSheet("background:#333; border-radius:4px; color:#555; font-size:14pt; font-weight:bold;")
        thumb_lbl.setText("PDF" if exists else "!")
        thumb_lbl.setObjectName(f"thumb_{path}")
        layout.addWidget(thumb_lbl, alignment=Qt.AlignHCenter)

        # Nome
        name_lbl = QLabel(short)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet(f"color:{'white' if exists else '#555'}; font-size:8pt; font-weight:bold; background:transparent;")
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)

        if not exists:
            err = QLabel("Arquivo não encontrado")
            err.setAlignment(Qt.AlignCenter)
            err.setStyleSheet("color:#c0392b; font-size:7pt; background:transparent;")
            layout.addWidget(err)

        # Clique para abrir
        if exists:
            card.setCursor(Qt.PointingHandCursor)
            card.mousePressEvent = lambda e, p=path: self.open_requested.emit(p)

        # Botão remover (×) sobreposto no canto
        btn_x = QPushButton("×", card)
        btn_x.setFixedSize(20, 20)
        btn_x.move(CARD_W - 26, 6)
        btn_x.setStyleSheet("""
            QPushButton { background:transparent; color:#444; font-size:13pt; border:none; }
            QPushButton:hover { color:#ff6b6b; }
        """)
        if mode == "library":
            btn_x.clicked.connect(lambda _, p=path: self._remove_library(p))
        else:
            btn_x.clicked.connect(lambda _, p=path: self._remove_recent(p))

        return card

    def _load_thumbs(self, items):
        """Carrega miniaturas em thread separada — emite sinal thread-safe ao terminar."""
        card_map_snapshot = dict(self._card_map)

        def worker():
            for item in items:
                path  = item["path"]
                if path not in card_map_snapshot:
                    continue
                thumb = get_thumbnail(path)
                if not thumb or not os.path.exists(thumb):
                    continue
                try:
                    img    = QImage(thumb).scaled(THUMB_W, THUMB_H,
                                                  Qt.KeepAspectRatio,
                                                  Qt.SmoothTransformation)
                    pixmap = QPixmap.fromImage(img)
                    self._thumb_ready.emit(path, pixmap)
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def _apply_thumb(self, path: str, pixmap: QPixmap):
        """Roda na thread principal — atualiza o card com a miniatura."""
        card = self._card_map.get(path)
        if card is None:
            return
        try:
            card.objectName()   # levanta RuntimeError se o objeto C++ foi deletado
            lbl = card.findChild(QLabel, f"thumb_{path}")
            if lbl:
                lbl.setPixmap(pixmap)
                lbl.setText("")
        except RuntimeError:
            pass

    # ------------------------------------------------------------------ Ações

    def add_to_library(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Adicionar PDFs à biblioteca",
            "", "Arquivos PDF (*.pdf *.PDF)"
        )
        for path in paths:
            add_to_library(path)
        if paths:
            self._show_library()

    def _remove_library(self, path):
        remove_from_library(path)
        self._show_library()

    def _remove_recent(self, path):
        remove_recent(path)
        self._show_recent()

    def refresh(self):
        if self._mode == "library":
            self._show_library()
        else:
            self._show_recent()