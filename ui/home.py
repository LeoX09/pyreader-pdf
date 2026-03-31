import os
import threading

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QPixmap, QImage, QDrag, QPainter, QColor

from qfluentwidgets import (
    SearchLineEdit, SmoothScrollArea, CardWidget,
    TransparentToolButton, PrimaryPushButton,
    SubtitleLabel, BodyLabel, CaptionLabel,
    FluentIcon as FI, TransparentPushButton
)

from core.library import load_library, add_to_library, remove_from_library, reorder_library
from core.history import load_recent, remove_recent
from core.thumbnail import get_thumbnail

CARD_W  = 160
CARD_H  = 260
THUMB_W = 140
THUMB_H = 200
COLS    = 5


class DraggableCard(CardWidget):
    open_requested   = Signal(str)
    remove_requested = Signal(str)
    drag_started     = Signal(object)
    dropped_on       = Signal(object)

    def __init__(self, item: dict, mode: str, parent=None):
        super().__init__(parent)
        self.path    = item["path"]
        self._mode   = mode
        self._drag_start_pos = None
        self._dragging       = False

        exists = os.path.exists(self.path)
        name   = item["name"].replace(".pdf","").replace(".PDF","")
        short  = name if len(name) <= 18 else name[:15] + "…"

        self.setFixedSize(CARD_W, CARD_H)
        if exists and mode == "library":
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        thumb_f = QFrame()
        thumb_f.setFixedSize(THUMB_W, THUMB_H)
        thumb_f.setStyleSheet("QFrame{background:#2d2d2d;border-radius:4px;border:none;}")
        tl = QVBoxLayout(thumb_f)
        tl.setContentsMargins(0, 0, 0, 0)
        self._thumb_lbl = QLabel()
        self._thumb_lbl.setFixedSize(THUMB_W, THUMB_H)
        self._thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_lbl.setStyleSheet("background:transparent;border:none;")
        if not exists:
            self._thumb_lbl.setText("✕")
            self._thumb_lbl.setStyleSheet("color:#c0392b;font-size:24pt;background:transparent;")
        else:
            self._thumb_lbl.setText("PDF")
            self._thumb_lbl.setStyleSheet("color:#555;font-size:14pt;font-weight:bold;background:transparent;")
        tl.addWidget(self._thumb_lbl)
        layout.addWidget(thumb_f, alignment=Qt.AlignmentFlag.AlignHCenter)

        name_lbl = CaptionLabel(short)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)

        btn_x = TransparentToolButton(FI.CLOSE, self)
        btn_x.setFixedSize(22, 22)
        btn_x.move(CARD_W - 28, 4)
        btn_x.clicked.connect(lambda: self.remove_requested.emit(self.path))

    def set_pixmap(self, pixmap: QPixmap):
        try:
            self._thumb_lbl.setPixmap(pixmap)
            self._thumb_lbl.setText("")
            self._thumb_lbl.setStyleSheet("background:transparent;")
        except RuntimeError:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._dragging:
            if self._drag_start_pos and \
               (event.pos() - self._drag_start_pos).manhattanLength() < 5:
                self.open_requested.emit(self.path)
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_start_pos is None or self._mode != "library":
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return
        self._dragging = True
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.path)
        drag.setMimeData(mime)
        ghost = self.grab()
        p = QPainter(ghost)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        p.fillRect(ghost.rect(), QColor(0, 0, 0, 160))
        p.end()
        drag.setPixmap(ghost)
        drag.setHotSpot(event.pos())
        self.drag_started.emit(self)
        drag.exec(Qt.DropAction.MoveAction)
        self._dragging = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and self._mode == "library":
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        pass

    def dropEvent(self, event):
        if event.mimeData().hasText() and self._mode == "library":
            self.dropped_on.emit(self)
            event.acceptProposedAction()


class HomeScreen(QWidget):
    open_requested = Signal(str)
    _thumb_ready   = Signal(str, QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._card_map    = {}
        self._items_order = []
        self._drag_source = None
        self._mode        = "library"
        self._search_text = ""
        self._all_items   = []
        self._thumb_ready.connect(self._apply_thumb)
        self.setObjectName("homeScreen")
        self.setStyleSheet("#homeScreen{background:#1f1f1f;}")
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        div = QFrame(); div.setFixedWidth(1)
        div.setStyleSheet("background:#333;")
        root.addWidget(div)
        self._main_area   = QWidget()
        self._main_layout = QVBoxLayout(self._main_area)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        root.addWidget(self._main_area, stretch=1)
        self._show_library()

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("background:#141414;")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        logo_w = QWidget()
        logo_w.setFixedHeight(72)
        logo_w.setStyleSheet("background:#141414;")
        ll = QHBoxLayout(logo_w)
        ll.setContentsMargins(18, 0, 18, 0)
        icon = QLabel("📖")
        icon.setStyleSheet("font-size:22pt;background:transparent;")
        name = SubtitleLabel("PyReaderPDF")
        ll.addWidget(icon)
        ll.addSpacing(8)
        ll.addWidget(name)
        ll.addStretch()
        layout.addWidget(logo_w)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background:#2a2a2a;")
        layout.addWidget(sep)
        layout.addSpacing(12)

        self._btn_library = self._nav_btn(FI.LIBRARY, "Biblioteca", self._show_library)
        self._btn_recent  = self._nav_btn(FI.HISTORY, "Recentes",   self._show_recent)
        layout.addWidget(self._btn_library)
        layout.addWidget(self._btn_recent)

        layout.addSpacing(12)
        sep2 = QFrame()
        sep2.setStyleSheet("background:#2a2a2a;margin:0 16px;")
        sep2.setFixedHeight(1)
        layout.addWidget(sep2)
        layout.addSpacing(12)

        btn_add = PrimaryPushButton(FI.ADD, "Adicionar PDF")
        btn_add.setFixedHeight(36)
        btn_add.clicked.connect(self.add_to_library)
        add_w = QWidget(); add_w.setStyleSheet("background:transparent;")
        al = QHBoxLayout(add_w)
        al.setContentsMargins(16, 0, 16, 0)
        al.addWidget(btn_add)
        layout.addWidget(add_w)
        layout.addStretch()

        ver = CaptionLabel("v0.6 — Fluent Design")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)
        layout.addSpacing(12)
        return sidebar

    def _nav_btn(self, icon, text: str, slot):
        btn = TransparentPushButton(icon, text)
        btn.setFixedHeight(42)
        btn.setFixedWidth(220)
        btn.clicked.connect(slot)
        return btn

    # ------------------------------------------------------------------ Seções

    def _clear_main(self):
        while self._main_layout.count():
            item = self._main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._card_map.clear()
        self._items_order.clear()

    def _show_library(self):
        self._mode = "library"
        self._clear_main()
        self._render_section("Biblioteca", load_library(), "library")

    def _show_recent(self):
        self._mode = "recent"
        self._clear_main()
        self._render_section("Recentes", load_recent(), "recent")

    def _render_section(self, title: str, items: list, mode: str):
        header = QWidget()
        header.setFixedHeight(64)
        header.setStyleSheet("background:#1f1f1f;border-bottom:1px solid #2a2a2a;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(28, 0, 24, 0)
        hl.setSpacing(12)

        t = SubtitleLabel(title)
        hl.addWidget(t)
        self._count_lbl = CaptionLabel(f"{len(items)} item{'s' if len(items)!=1 else ''}")
        hl.addWidget(self._count_lbl)
        hl.addStretch()

        self._search_box = SearchLineEdit()
        self._search_box.setPlaceholderText("Buscar por nome ou palavra-chave…")
        self._search_box.setFixedSize(300, 34)
        self._search_box.textChanged.connect(self._on_search)
        hl.addWidget(self._search_box)
        self._main_layout.addWidget(header)

        if not items:
            self._main_layout.addWidget(self._empty_state())
            return

        self._scroll = SmoothScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea{border:none;background:#1f1f1f;}")

        self._container = QWidget()
        self._container.setStyleSheet("background:#1f1f1f;")
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(24, 20, 24, 24)
        self._grid.setSpacing(16)

        self._all_items   = items
        self._items_order = [it["path"] for it in items]
        self._populate_grid(items, mode)

        self._scroll.setWidget(self._container)
        self._main_layout.addWidget(self._scroll, stretch=1)
        self._load_thumbs(items)

    def _populate_grid(self, items: list, mode: str = None):
        if mode is None:
            mode = self._mode
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self._card_map.clear()

        for i, item in enumerate(items):
            card = DraggableCard(item, mode)
            card.open_requested.connect(self.open_requested)
            card.drag_started.connect(self._on_drag_started)
            card.dropped_on.connect(self._on_dropped_on)
            if mode == "library":
                card.remove_requested.connect(self._remove_library)
            else:
                card.remove_requested.connect(self._remove_recent)
            self._grid.addWidget(card, i // COLS, i % COLS, Qt.AlignmentFlag.AlignTop)
            self._card_map[item["path"]] = card
        self._grid.setRowStretch(self._grid.rowCount(), 1)

    def _on_search(self, text: str):
        self._search_text = text.lower().strip()
        filtered = self._all_items if not self._search_text else [
            it for it in self._all_items
            if self._search_text in it["name"].lower()
            or self._search_text in it["path"].lower()
        ]
        self._populate_grid(filtered)
        self._count_lbl.setText(f"{len(filtered)} item{'s' if len(filtered)!=1 else ''}")
        self._load_thumbs(filtered)

    def _on_drag_started(self, card):
        self._drag_source = card

    def _on_dropped_on(self, target):
        if not self._drag_source or self._drag_source is target:
            self._drag_source = None
            return
        src_path = self._drag_source.path
        tgt_path = target.path
        if src_path not in self._items_order or tgt_path not in self._items_order:
            self._drag_source = None
            return
        src_i = self._items_order.index(src_path)
        tgt_i = self._items_order.index(tgt_path)
        self._items_order.insert(tgt_i, self._items_order.pop(src_i))
        reorder_library(self._items_order)
        order_map = {p: i for i, p in enumerate(self._items_order)}
        self._all_items = sorted(self._all_items, key=lambda it: order_map.get(it["path"], 9999))
        self._populate_grid(self._all_items)
        self._load_thumbs(self._all_items)
        self._drag_source = None

    def _load_thumbs(self, items: list):
        def worker():
            for item in items:
                path  = item["path"]
                thumb = get_thumbnail(path)
                if not thumb or not os.path.exists(thumb):
                    continue
                try:
                    img    = QImage(thumb).scaled(THUMB_W, THUMB_H,
                                                  Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation)
                    pixmap = QPixmap.fromImage(img)
                    self._thumb_ready.emit(path, pixmap)
                except Exception:
                    pass
        threading.Thread(target=worker, daemon=True).start()

    def _apply_thumb(self, path: str, pixmap: QPixmap):
        card = self._card_map.get(path)
        if card:
            try:
                card.set_pixmap(pixmap)
            except RuntimeError:
                pass

    def _empty_state(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel("📚")
        icon.setStyleSheet("font-size:52pt;background:transparent;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg = SubtitleLabel("Nenhum item ainda")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = BodyLabel("Use '+ Adicionar PDF' para começar")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(icon); l.addSpacing(8)
        l.addWidget(msg); l.addWidget(sub)
        return w

    def add_to_library(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Adicionar PDFs", "", "PDF (*.pdf *.PDF)")
        for p in paths:
            add_to_library(p)
        if paths:
            self._show_library()

    def _remove_library(self, path: str):
        remove_from_library(path)
        self._show_library()

    def _remove_recent(self, path: str):
        remove_recent(path)
        self._show_recent()

    def refresh(self):
        if self._mode == "library":
            self._show_library()
        else:
            self._show_recent()