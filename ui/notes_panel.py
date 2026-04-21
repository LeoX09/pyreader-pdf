from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor

from core.notes import load_notes, save_note, update_note, delete_note

COLORS = ["#f6c90e", "#2ecc71", "#e74c3c", "#3498db", "#9b59b6"]


class NoteCard(QFrame):
    """Card de uma nota com citação e campo de texto editável."""
    deleted   = Signal(int)
    changed   = Signal(int, str)
    go_to_page = Signal(int)

    def __init__(self, note: dict, parent=None):
        super().__init__(parent)
        self._note_id = note["id"]
        self._page    = note["page"]
        color         = note.get("color", "#f6c90e")

        self.setStyleSheet(f"""
            QFrame {{
                background: #1e1e1e;
                border-left: 3px solid {color};
                border-radius: 0 6px 6px 0;
                margin: 2px 0;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Header: página + botão deletar
        header = QHBoxLayout()
        pg = QPushButton(f"Pág. {note['page'] + 1}")
        pg.setFlat(True)
        pg.setStyleSheet(f"""
            QPushButton {{
                color: {color}; font-size: 8pt; font-weight: bold;
                background: transparent; border: none; text-align: left;
            }}
            QPushButton:hover {{ text-decoration: underline; }}
        """)
        pg.setCursor(Qt.PointingHandCursor)
        pg.clicked.connect(lambda: self.go_to_page.emit(self._page))
        header.addWidget(pg)

        date = QLabel(note.get("created", ""))
        date.setStyleSheet("color:#333; font-size:7pt; background:transparent;")
        header.addWidget(date)
        header.addStretch()

        btn_del = QPushButton("×")
        btn_del.setFixedSize(18, 18)
        btn_del.setStyleSheet("""
            QPushButton { background:transparent; color:#333; border:none; font-size:12pt; }
            QPushButton:hover { color:#ff6b6b; }
        """)
        btn_del.clicked.connect(lambda: self.deleted.emit(self._note_id))
        header.addWidget(btn_del)
        layout.addLayout(header)

        # Citação
        quote = QLabel(f'"{note["quote"]}"')
        quote.setWordWrap(True)
        quote.setStyleSheet(f"""
            color: #aaa; font-size: 8pt; font-style: italic;
            background: transparent;
            padding: 4px 6px;
            border-radius: 4px;
        """)
        layout.addWidget(quote)

        # Nota editável
        self._editor = QTextEdit()
        self._editor.setPlaceholderText("Adicionar nota…")
        self._editor.setText(note.get("note", ""))
        self._editor.setMaximumHeight(80)
        self._editor.setStyleSheet("""
            QTextEdit {
                background: #252525; color: #d0d0d0;
                border: 1px solid #333; border-radius: 4px;
                font-size: 9pt; padding: 4px;
            }
            QTextEdit:focus { border-color: #444; }
        """)
        self._editor.textChanged.connect(
            lambda: self.changed.emit(self._note_id, self._editor.toPlainText()))
        layout.addWidget(self._editor)


class NotesPanel(QWidget):
    """
    Painel lateral de notas — desliza para dentro/fora.
    Recebe citações via add_citation() chamado pelo PDFTab.
    """

    go_to_page_requested = Signal(int)   # page_index (0-based)
    close_requested      = Signal()

    def __init__(self, pdf_path: str, parent=None):
        super().__init__(parent)
        self._pdf_path = pdf_path
        self.setFixedWidth(300)
        self.setStyleSheet("background:#161616; border-left:1px solid #222;")
        self._build()
        self._load_notes()

    # ------------------------------------------------------------------ Build

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet("background:#111; border-bottom:1px solid #222;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 0, 10, 0)

        title = QLabel("📝  Notas")
        title.setStyleSheet("color:white; font-size:10pt; font-weight:bold; background:transparent;")
        hl.addWidget(title)
        hl.addStretch()

        self._count_lbl = QLabel("0")
        self._count_lbl.setStyleSheet("color:#444; font-size:8pt; background:transparent;")
        hl.addWidget(self._count_lbl)

        btn_close = QPushButton("×")
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setToolTip("Fechar painel de notas")
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent; color: #555; border: none;
                font-size: 14pt;
            }
            QPushButton:hover { color: #ff6b6b; }
        """)
        btn_close.clicked.connect(self.close_requested)
        hl.addWidget(btn_close)

        layout.addWidget(header)

        # Dica
        self._hint = QLabel("Selecione texto no PDF\ne pressione Ctrl+Shift+N\npara criar uma nota")
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setStyleSheet("color:#333; font-size:9pt; background:transparent; padding:20px;")

        # Scroll com cards
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("""
            QScrollArea { border:none; background:#161616; }
            QScrollBar:vertical { background:#1a1a1a; width:5px; border-radius:2px; }
            QScrollBar::handle:vertical { background:#333; border-radius:2px; }
        """)

        self._cards_widget = QWidget()
        self._cards_widget.setStyleSheet("background:#161616;")
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(8, 8, 8, 8)
        self._cards_layout.setSpacing(6)
        self._cards_layout.addStretch()

        self._scroll.setWidget(self._cards_widget)
        layout.addWidget(self._scroll, stretch=1)

    # ------------------------------------------------------------------ Notas

    def _load_notes(self):
        """Carrega notas existentes do arquivo."""
        for note in load_notes(self._pdf_path):
            self._add_card(note)
        self._update_count()

    def add_citation(self, text: str, page_index: int, color: str = "#f6c90e"):
        """Chamado pelo PDFTab quando o usuário seleciona texto."""
        note = save_note(self._pdf_path, page_index, text, color=color)
        self._add_card(note)
        self._update_count()
        # Scrolla para a nova nota
        self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum())

    def _add_card(self, note: dict):
        card = NoteCard(note, self)
        card.deleted.connect(self._delete_note)
        card.changed.connect(lambda nid, txt: update_note(self._pdf_path, nid, txt))
        card.go_to_page.connect(self.go_to_page_requested)
        # Insere antes do stretch
        idx = self._cards_layout.count() - 1
        self._cards_layout.insertWidget(idx, card)

    def _delete_note(self, note_id: int):
        delete_note(self._pdf_path, note_id)
        # Remove o card da UI
        for i in range(self._cards_layout.count()):
            item = self._cards_layout.itemAt(i)
            if item and isinstance(item.widget(), NoteCard):
                if item.widget()._note_id == note_id:
                    item.widget().deleteLater()
                    self._cards_layout.removeItem(item)
                    break
        self._update_count()

    def _update_count(self):
        n = sum(1 for i in range(self._cards_layout.count())
                if isinstance(self._cards_layout.itemAt(i).widget(), NoteCard))
        self._count_lbl.setText(str(n) if n else "")