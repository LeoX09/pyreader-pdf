import fitz
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                QPushButton, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt, Signal

class SidebarPanel(QWidget):
    topic_requested    = Signal(int)
    visibility_changed = Signal(bool)

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self._doc = doc
        self.setMinimumWidth(100)
        self.setStyleSheet("background:#161616;")
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(36)
        header.setStyleSheet("background:#111;border-bottom:1px solid #222;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(8, 0, 4, 0)
        hl.setSpacing(2)

        title = QPushButton("Tópicos")
        title.setEnabled(False)
        title.setStyleSheet("""
            QPushButton{background:transparent;color:white;border:none;
                        font-size:8pt;padding:0 6px;}
        """)
        hl.addWidget(title)
        hl.addStretch()

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
            hl.addWidget(b)

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

        # Tree
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
        root.addWidget(self._tree)

    def _load_toc(self):
        toc = self._doc.get_toc()
        if not toc:
            item = QTreeWidgetItem(["Sem índice disponível"])
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._tree.addTopLevelItem(item)
            return

        stack = []
        for level, title, page, *_ in toc:
            item = QTreeWidgetItem([title])
            item.setData(0, Qt.ItemDataRole.UserRole, page - 1)
            item.setToolTip(0, f"Pág. {page}")
            while stack and stack[-1][0] >= level:
                stack.pop()
            if stack:
                stack[-1][1].addChild(item)
            else:
                self._tree.addTopLevelItem(item)
            stack.append((level, item))

        self._tree.expandToDepth(0)

    def _on_topic_clicked(self, item: QTreeWidgetItem, col: int):
        page = item.data(0, Qt.ItemDataRole.UserRole)
        if page is not None:
            self.topic_requested.emit(page)

    def collapse(self):
        self.hide()
        self.visibility_changed.emit(False)