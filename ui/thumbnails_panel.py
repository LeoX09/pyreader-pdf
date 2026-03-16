import fitz
import threading
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                                QLabel, QFrame, QPushButton, QStackedWidget,
                                QTreeWidget, QTreeWidgetItem, QAbstractScrollArea)
from PySide6.QtCore import Qt, Signal, QMetaObject, QThreadPool, QRunnable, QObject, QTimer
from PySide6.QtGui import QPixmap, QImage

THUMB_W     = 150
THUMB_H     = 190
PANEL_W     = 190
RENDER_ZOOM = 0.35
MAX_THREADS = 2   # limita renders simultâneos para não travar


class ThumbSignals(QObject):
    done = Signal(int, QPixmap)


class ThumbWorker(QRunnable):
    """Abre o PDF pelo path (nunca compartilha doc entre threads)."""
    def __init__(self, pdf_path: str, index: int, signals: ThumbSignals):
        super().__init__()
        self._path    = pdf_path
        self._index   = index
        self._signals = signals
        self.setAutoDelete(True)

    def run(self):
        try:
            doc    = fitz.open(self._path)   # novo doc por thread — thread-safe
            page   = doc[self._index]
            mat    = fitz.Matrix(RENDER_ZOOM, RENDER_ZOOM)
            pix    = page.get_pixmap(matrix=mat, alpha=False)
            img    = QImage(pix.samples, pix.width, pix.height,
                            pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img.copy())
            doc.close()
            self._signals.done.emit(self._index, pixmap)
        except Exception:
            pass


class ThumbnailCard(QWidget):
    clicked = Signal(int)

    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self._index  = index
        self._active = False
        self.setFixedWidth(PANEL_W)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 4)
        layout.setSpacing(3)

        self._frame = QFrame()
        self._frame.setFixedSize(THUMB_W, THUMB_H)
        self._frame.setStyleSheet(
            "QFrame{background:#2a2a2a;border:1px solid #333;border-radius:3px;}")
        fl = QVBoxLayout(self._frame)
        fl.setContentsMargins(0, 0, 0, 0)

        self._img = QLabel()
        self._img.setFixedSize(THUMB_W, THUMB_H)
        self._img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img.setStyleSheet("background:transparent;border:none;")
        fl.addWidget(self._img)

        layout.addWidget(self._frame, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._num = QLabel(str(self._index + 1))
        self._num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._num.setStyleSheet("color:#555;font-size:7pt;background:transparent;")
        layout.addWidget(self._num)

    def set_pixmap(self, pixmap: QPixmap):
        self._img.setPixmap(pixmap.scaled(
            THUMB_W, THUMB_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def set_active(self, active: bool):
        self._active = active
        self._frame.setStyleSheet(
            f"QFrame{{background:{'#1e2a35' if active else '#2a2a2a'};"
            f"border:{'2px solid #2980b9' if active else '1px solid #333'};"
            f"border-radius:3px;}}")
        self._num.setStyleSheet(
            f"color:{'white' if active else '#555'};font-size:7pt;background:transparent;")

    def mousePressEvent(self, event):
        self.clicked.emit(self._index)


class SidebarPanel(QWidget):
    page_requested     = Signal(int)
    topic_requested    = Signal(int)
    visibility_changed = Signal(bool)

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self._doc      = doc
        self._path     = doc.name   # path para threads abertas separadamente
        self._cards    = []
        self._active   = 0
        self._rendered = set()   # páginas já renderizadas
        self._pool     = QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(MAX_THREADS)
        self._signals  = ThumbSignals()
        self._signals.done.connect(self._on_thumb_done)
        self.setMinimumWidth(100)
        self.setStyleSheet("background:#161616;")
        self._build()
        # Lazy load: começa após a UI estar pronta
        QTimer.singleShot(200, self._load_visible)

    # ------------------------------------------------------------------ Layout

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(36)
        header.setStyleSheet("background:#111;border-bottom:1px solid #222;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(4, 0, 4, 0)
        hl.setSpacing(2)

        self._btn_pages  = self._tab_btn("Páginas",  lambda: self._switch(0))
        self._btn_topics = self._tab_btn("Tópicos",  lambda: self._switch(1))
        hl.addWidget(self._btn_pages)
        hl.addWidget(self._btn_topics)
        hl.addStretch()

        btn_collapse = QPushButton("‹")
        btn_collapse.setFixedSize(22, 22)
        btn_collapse.setToolTip("Minimizar painel")
        btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_collapse.setStyleSheet("""
            QPushButton{background:transparent;color:#555;border:none;
                        font-size:13pt;border-radius:3px;}
            QPushButton:hover{color:white;background:#2a2a2a;}
        """)
        btn_collapse.clicked.connect(self.collapse)
        hl.addWidget(btn_collapse)
        root.addWidget(header)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_pages())
        self._stack.addWidget(self._build_topics())
        root.addWidget(self._stack, stretch=1)

        self._set_tab_active(self._btn_pages)

    def _tab_btn(self, text, slot):
        btn = QPushButton(text)
        btn.setFixedHeight(24)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton{background:transparent;color:#555;border:none;
                        font-size:8pt;padding:0 6px;border-radius:3px;}
            QPushButton:hover{color:#aaa;}
        """)
        btn.clicked.connect(slot)
        return btn

    def _set_tab_active(self, active_btn):
        for b in (self._btn_pages, self._btn_topics):
            is_a = b is active_btn
            b.setStyleSheet(f"""
                QPushButton{{background:{"#2a2a2a" if is_a else "transparent"};
                    color:{"white" if is_a else "#555"};border:none;
                    font-size:8pt;padding:0 6px;border-radius:3px;}}
                QPushButton:hover{{color:#aaa;}}
            """)

    def _switch(self, index: int):
        self._stack.setCurrentIndex(index)
        self._set_tab_active(self._btn_pages if index == 0 else self._btn_topics)
        if index == 0:
            QTimer.singleShot(50, self._load_visible)

    # ------------------------------------------------------------------ Páginas

    def _build_pages(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:#161616;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea{border:none;background:#161616;}
            QScrollBar:vertical{background:#1a1a1a;width:4px;border-radius:2px;}
            QScrollBar::handle:vertical{background:#333;border-radius:2px;}
            QScrollBar::handle:vertical:hover{background:#444;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
        """)
        scroll.verticalScrollBar().valueChanged.connect(
            lambda: QTimer.singleShot(100, self._load_visible))

        container = QWidget()
        container.setStyleSheet("background:#161616;")
        self._pages_vbox = QVBoxLayout(container)
        self._pages_vbox.setContentsMargins(0, 6, 0, 6)
        self._pages_vbox.setSpacing(0)

        for i in range(len(self._doc)):
            card = ThumbnailCard(i)
            card.clicked.connect(self._on_page_clicked)
            self._pages_vbox.addWidget(card)
            self._cards.append(card)

        self._pages_vbox.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self._pages_scroll = scroll
        return w

    # ------------------------------------------------------------------ Lazy load

    def _load_visible(self):
        """Renderiza apenas as miniaturas visíveis na viewport."""
        if not self._cards:
            return
        scroll = self._pages_scroll
        vp_top    = scroll.verticalScrollBar().value()
        vp_bottom = vp_top + scroll.viewport().height()

        for i, card in enumerate(self._cards):
            if i in self._rendered:
                continue
            card_top = card.mapTo(scroll.widget(), card.rect().topLeft()).y()
            card_bot = card_top + card.height()
            # Margem de pré-carregamento
            if card_bot >= vp_top - 200 and card_top <= vp_bottom + 200:
                self._rendered.add(i)
                worker = ThumbWorker(self._path, i, self._signals)
                self._pool.start(worker)

    def _on_thumb_done(self, index: int, pixmap: QPixmap):
        if 0 <= index < len(self._cards):
            try:
                self._cards[index].set_pixmap(pixmap)
            except RuntimeError:
                pass

    # ------------------------------------------------------------------ Tópicos

    def _build_topics(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:#161616;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QWidget()
        toolbar.setFixedHeight(28)
        toolbar.setStyleSheet("background:#111;border-bottom:1px solid #1e1e1e;")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(6, 0, 6, 0)
        tl.setSpacing(2)

        for icon, tip, slot in [
            ("⊞", "Expandir tudo",  lambda: self._tree.expandAll()),
            ("⊟", "Colapsar tudo", lambda: self._tree.collapseAll()),
        ]:
            b = QPushButton(icon)
            b.setFixedSize(20, 20)
            b.setToolTip(tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton{background:transparent;color:#555;border:none;
                            font-size:10pt;border-radius:3px;}
                QPushButton:hover{color:white;background:#2a2a2a;}
            """)
            b.clicked.connect(slot)
            tl.addWidget(b)
        tl.addStretch()
        layout.addWidget(toolbar)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setIndentation(12)
        self._tree.setStyleSheet("""
            QTreeWidget{background:#161616;border:none;color:#aaa;font-size:8pt;}
            QTreeWidget::item{padding:4px 6px;border-radius:3px;}
            QTreeWidget::item:hover{background:#1e1e1e;color:white;}
            QTreeWidget::item:selected{background:#1e2a35;color:white;}
            QTreeWidget::branch{background:#161616;}
            QScrollBar:vertical{background:#1a1a1a;width:4px;border-radius:2px;}
            QScrollBar::handle:vertical{background:#333;border-radius:2px;}
            QScrollBar::handle:vertical:hover{background:#444;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
        """)
        self._tree.itemClicked.connect(self._on_topic_clicked)
        self._load_toc()
        layout.addWidget(self._tree)
        return w

    def _load_toc(self):
        toc = self._doc.get_toc()
        if not toc:
            item = QTreeWidgetItem(["Sem índice disponível"])
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._tree.addTopLevelItem(item)
            return

        stack = []
        for level, title, page, *_ in toc:
            item = QTreeWidgetItem()
            item.setData(0, Qt.ItemDataRole.UserRole,     page - 1)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, title)
            item.setToolTip(0, f"Pág. {page}")
            while stack and stack[-1][0] >= level:
                stack.pop()
            if stack:
                stack[-1][1].addChild(item)
            else:
                self._tree.addTopLevelItem(item)
            stack.append((level, item))

        self._setup_item_widgets(self._tree.invisibleRootItem(), 0)
        self._tree.expandToDepth(0)

    def _setup_item_widgets(self, parent_item, level: int):
        for i in range(parent_item.childCount()):
            item  = parent_item.child(i)
            has_c = item.childCount() > 0
            page  = item.data(0, Qt.ItemDataRole.UserRole)
            title = item.data(0, Qt.ItemDataRole.UserRole + 1) or ""

            w = QWidget()
            w.setStyleSheet("background:transparent;")
            hl = QHBoxLayout(w)
            hl.setContentsMargins(level * 8 + 4, 1, 4, 1)
            hl.setSpacing(2)

            if has_c:
                btn = QPushButton("▾")
                btn.setFixedSize(16, 16)
                btn.setStyleSheet("""
                    QPushButton{background:transparent;color:#555;border:none;
                                font-size:8pt;border-radius:2px;padding:0;}
                    QPushButton:hover{color:white;background:#2a2a2a;}
                """)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(
                    lambda _, it=item, b=btn: self._toggle_item(it, b))
                hl.addWidget(btn)
            else:
                sp = QWidget()
                sp.setFixedSize(16, 16)
                sp.setStyleSheet("background:transparent;")
                hl.addWidget(sp)

            lbl = QLabel(title)
            lbl.setStyleSheet(f"""
                color:{'#ddd' if level == 0 else '#aaa'};
                font-size:8pt;
                {'font-weight:bold;' if level == 0 else ''}
                background:transparent;
            """)
            lbl.setWordWrap(False)
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            if page is not None:
                lbl.mousePressEvent = lambda e, p=page: self.topic_requested.emit(p)
            hl.addWidget(lbl, stretch=1)

            self._tree.setItemWidget(item, 0, w)
            self._setup_item_widgets(item, level + 1)

    def _toggle_item(self, item, btn: QPushButton):
        if item.isExpanded():
            item.setExpanded(False)
            btn.setText("▸")
        else:
            item.setExpanded(True)
            btn.setText("▾")

    def _on_topic_clicked(self, item: QTreeWidgetItem, col: int):
        page = item.data(0, Qt.ItemDataRole.UserRole)
        if page is not None:
            self.topic_requested.emit(page)

    # ------------------------------------------------------------------ API

    def set_current_page(self, page_index: int):
        if page_index == self._active:
            return
        if 0 <= self._active < len(self._cards):
            self._cards[self._active].set_active(False)
        self._active = page_index
        if 0 <= page_index < len(self._cards):
            self._cards[page_index].set_active(True)
            self._pages_scroll.ensureWidgetVisible(self._cards[page_index], 0, 40)
        self._load_visible()

    def _on_page_clicked(self, index: int):
        self.set_current_page(index)
        self.page_requested.emit(index)

    def collapse(self):
        self.hide()
        self.visibility_changed.emit(False)