import os
import threading

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QFileDialog, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QBrush, QLinearGradient

from core.library import load_library, add_to_library, remove_from_library
from core.history import load_recent, remove_recent
from core.thumbnail import get_thumbnail

CARD_W = 160
CARD_H = 260
THUMB_W = 140
THUMB_H = 200


class HomeScreen(QWidget):
    open_requested = Signal(str)
    _thumb_ready   = Signal(str, QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._card_map = {}
        self._mode = "library"
        self._thumb_ready.connect(self._apply_thumb)
        self.setStyleSheet("background:#141414;")
        self._build()

    # ------------------------------------------------------------------ Layout

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        div = QFrame()
        div.setFixedWidth(1)
        div.setStyleSheet("background:#222;")
        root.addWidget(div)

        self._main_area   = QWidget()
        self._main_layout = QVBoxLayout(self._main_area)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self._main_area.setStyleSheet("background:#141414;")
        root.addWidget(self._main_area, stretch=1)

        self._show_library()

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet("background:#111;")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo
        logo_w = QWidget()
        logo_w.setFixedHeight(70)
        logo_w.setStyleSheet("background:#111;")
        ll = QHBoxLayout(logo_w)
        ll.setContentsMargins(20, 0, 20, 0)
        icon = QLabel("📖")
        icon.setStyleSheet("font-size:20pt; background:transparent;")
        name = QLabel("PyReaderPDF")
        name.setStyleSheet("color:white; font-size:11pt; font-weight:bold; background:transparent;")
        ll.addWidget(icon)
        ll.addWidget(name)
        ll.addStretch()
        layout.addWidget(logo_w)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#222;")
        layout.addWidget(sep)

        layout.addSpacing(12)

        self._btn_library = self._nav_btn("⊟", "Biblioteca",  self._show_library)
        self._btn_recent  = self._nav_btn("⊙", "Recentes",    self._show_recent)
        layout.addWidget(self._btn_library)
        layout.addWidget(self._btn_recent)

        layout.addSpacing(8)
        sep2 = QFrame()
        sep2.setStyleSheet("background:#222; margin:0 16px;")
        sep2.setFixedHeight(1)
        layout.addWidget(sep2)
        layout.addSpacing(8)

        btn_add = QPushButton("  ＋  Adicionar PDF")
        btn_add.setFixedHeight(38)
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1a6b3c, stop:1 #145c32);
                color: white; border: none; border-radius: 6px;
                font-size: 9pt; font-weight: bold;
                margin: 0 12px;
            }
            QPushButton:hover { background: #1f8048; }
            QPushButton:pressed { background: #145c32; }
        """)
        btn_add.clicked.connect(self.add_to_library)
        layout.addWidget(btn_add)

        layout.addStretch()

        # Versão
        ver = QLabel("v0.5 — PySide6")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet("color:#333; font-size:7pt; background:transparent; padding:12px;")
        layout.addWidget(ver)

        return sidebar

    def _nav_btn(self, icon: str, text: str, slot) -> QPushButton:
        btn = QPushButton(f"  {icon}  {text}")
        btn.setFixedHeight(40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFlat(True)
        btn.setStyleSheet("""
            QPushButton {
                color: #888; text-align: left;
                font-size: 10pt; background: transparent;
                border: none; border-radius: 0;
                padding-left: 8px;
            }
            QPushButton:hover { color: #ccc; background: #1a1a1a; }
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
        self._set_active(self._btn_library)
        self._clear_main()
        self._render_section("Biblioteca", load_library(), "library")

    def _show_recent(self):
        self._mode = "recent"
        self._set_active(self._btn_recent)
        self._clear_main()
        self._render_section("Recentes", load_recent(), "recent")

    def _set_active(self, active):
        for btn in (self._btn_library, self._btn_recent):
            is_active = btn is active
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {"white" if is_active else "#888"};
                    text-align: left; font-size: 10pt;
                    background: {"#1e1e1e" if is_active else "transparent"};
                    border: none;
                    border-left: {"3px solid #2980b9" if is_active else "3px solid transparent"};
                    padding-left: 8px;
                }}
                QPushButton:hover {{ color: #ccc; background: #1a1a1a; }}
            """)

    def _render_section(self, title: str, items: list, mode: str):
        # Header
        header = QWidget()
        header.setFixedHeight(64)
        header.setStyleSheet("background:#141414; border-bottom:1px solid #1e1e1e;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(28, 0, 28, 0)

        t = QLabel(title)
        t.setStyleSheet("color:white; font-size:15pt; font-weight:bold; background:transparent;")
        hl.addWidget(t)

        c = QLabel(f"{len(items)} item{'s' if len(items) != 1 else ''}")
        c.setStyleSheet("color:#444; font-size:9pt; background:transparent; padding-left:8px;")
        hl.addWidget(c)
        hl.addStretch()
        self._main_layout.addWidget(header)

        if not items:
            self._main_layout.addWidget(self._empty_state())
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none; background:#141414;} QScrollBar:vertical{background:#1a1a1a; width:6px; border-radius:3px;} QScrollBar::handle:vertical{background:#333; border-radius:3px;} QScrollBar::handle:vertical:hover{background:#444;} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}")

        container = QWidget()
        container.setStyleSheet("background:#141414;")
        grid = QGridLayout(container)
        grid.setContentsMargins(24, 20, 24, 24)
        grid.setSpacing(16)

        cols = 5
        for i, item in enumerate(items):
            card = self._make_card(item, mode)
            grid.addWidget(card, i // cols, i % cols, Qt.AlignTop)
            self._card_map[item["path"]] = card

        grid.setRowStretch(grid.rowCount(), 1)
        scroll.setWidget(container)
        self._main_layout.addWidget(scroll, stretch=1)

        self._load_thumbs(items)

    def _empty_state(self):
        w = QWidget()
        w.setStyleSheet("background:#141414;")
        l = QVBoxLayout(w)
        l.setAlignment(Qt.AlignCenter)

        icon = QLabel("📚")
        icon.setStyleSheet("font-size:52pt; background:transparent;")
        icon.setAlignment(Qt.AlignCenter)

        msg = QLabel("Nenhum item ainda")
        msg.setStyleSheet("color:#555; font-size:12pt; font-weight:bold; background:transparent;")
        msg.setAlignment(Qt.AlignCenter)

        sub = QLabel("Use '+ Adicionar PDF' para começar")
        sub.setStyleSheet("color:#333; font-size:9pt; background:transparent;")
        sub.setAlignment(Qt.AlignCenter)

        l.addWidget(icon)
        l.addSpacing(8)
        l.addWidget(msg)
        l.addWidget(sub)
        return w

    # ------------------------------------------------------------------ Card

    def _make_card(self, item: dict, mode: str) -> QFrame:
        path   = item["path"]
        name   = item["name"].replace(".pdf","").replace(".PDF","")
        exists = os.path.exists(path)
        short  = name if len(name) <= 18 else name[:15] + "…"

        card = QFrame()
        card.setFixedSize(CARD_W, CARD_H)
        card.setStyleSheet("""
            QFrame {
                background: #1c1c1c;
                border-radius: 8px;
                border: 1px solid #252525;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Thumb container
        thumb_container = QFrame()
        thumb_container.setFixedSize(THUMB_W, THUMB_H)
        thumb_container.setStyleSheet("""
            QFrame {
                background: #252525;
                border-radius: 4px;
                border: none;
            }
        """)
        tl = QVBoxLayout(thumb_container)
        tl.setContentsMargins(0, 0, 0, 0)

        thumb_lbl = QLabel()
        thumb_lbl.setFixedSize(THUMB_W, THUMB_H)
        thumb_lbl.setAlignment(Qt.AlignCenter)
        thumb_lbl.setObjectName(f"thumb_{path}")
        if not exists:
            thumb_lbl.setText("✕")
            thumb_lbl.setStyleSheet("color:#c0392b; font-size:24pt; background:transparent;")
        else:
            thumb_lbl.setText("PDF")
            thumb_lbl.setStyleSheet("color:#444; font-size:14pt; font-weight:bold; background:transparent;")
        tl.addWidget(thumb_lbl)
        layout.addWidget(thumb_container, alignment=Qt.AlignHCenter)

        # Nome
        name_lbl = QLabel(short)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet(f"""
            color: {"#d0d0d0" if exists else "#555"};
            font-size: 8pt;
            font-weight: {"600" if exists else "400"};
            background: transparent;
        """)
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)

        # Botão remover
        btn_x = QPushButton("×", card)
        btn_x.setFixedSize(22, 22)
        btn_x.move(CARD_W - 28, 4)
        btn_x.setStyleSheet("""
            QPushButton { background:rgba(0,0,0,0); color:#333; border:none; font-size:14pt; border-radius:4px; }
            QPushButton:hover { color:#ff6b6b; background:rgba(255,107,107,0.1); }
        """)
        if mode == "library":
            btn_x.clicked.connect(lambda _, p=path: self._remove_library(p))
        else:
            btn_x.clicked.connect(lambda _, p=path: self._remove_recent(p))

        # Hover e clique
        if exists:
            card.setCursor(Qt.PointingHandCursor)
            card.mousePressEvent = lambda e, p=path: self.open_requested.emit(p)

            def enter(e, c=card):
                c.setStyleSheet("""
                    QFrame { background:#222; border-radius:8px; border:1px solid #2980b9; }
                """)
            def leave(e, c=card):
                c.setStyleSheet("""
                    QFrame { background:#1c1c1c; border-radius:8px; border:1px solid #252525; }
                """)
            card.enterEvent = enter
            card.leaveEvent = leave

        return card

    def _load_thumbs(self, items):
        snapshot = dict(self._card_map)

        def worker():
            for item in items:
                path  = item["path"]
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
        card = self._card_map.get(path)
        if not card:
            return
        try:
            card.objectName()
            lbl = card.findChild(QLabel, f"thumb_{path}")
            if lbl:
                lbl.setPixmap(pixmap)
                lbl.setText("")
                lbl.setStyleSheet("background:transparent;")
        except RuntimeError:
            pass

    # ------------------------------------------------------------------ Ações

    def add_to_library(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Adicionar PDFs", "", "PDF (*.pdf *.PDF)")
        for p in paths:
            add_to_library(p)
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