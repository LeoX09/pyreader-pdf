"""
core/theme.py
Identidade visual do PyReaderPDF — "Biblioteca às 22h"
Paleta: charcoal quente + âmbar. Tipografia: UI limpa, sem azul de tech.
"""

STYLESHEET = """
/* ── Janela principal ─────────────────────────────────────── */
QMainWindow, QDialog {
    background: #1a1814;
}

/* ── Toolbar ─────────────────────────────────────────────── */
QToolBar {
    background: #211f1b;
    border-bottom: 1px solid #3d3830;
    padding: 4px 8px;
    spacing: 4px;
}

QToolBar::separator {
    background: #3d3830;
    width: 1px;
    margin: 6px 4px;
}

QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: #a89880;
    padding: 4px 10px;
    font-size: 9pt;
}

QToolButton:hover {
    background: #2a2722;
    border-color: #3d3830;
    color: #e8e0d0;
}

QToolButton:pressed, QToolButton:checked {
    background: #332f28;
    border-color: #6b4e18;
    color: #c8922a;
}

QToolButton:disabled {
    color: #4a4238;
}

/* ── Tabs ────────────────────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background: #1a1814;
}

QTabBar {
    background: #211f1b;
    border-bottom: 1px solid #3d3830;
}

QTabBar::tab {
    background: transparent;
    color: #6b6050;
    padding: 6px 16px;
    margin-right: 2px;
    font-size: 9pt;
    min-width: 80px;
    border: 1px solid transparent;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
}

QTabBar::tab:hover:!selected {
    background: #2a2722;
    color: #a89880;
}

QTabBar::tab:selected {
    background: #1a1814;
    color: #e8e0d0;
    border-color: #3d3830;
    border-bottom-color: #1a1814;
}

QTabBar::close-button {
    image: none;
    subcontrol-position: right;
}

/* ── Status bar ──────────────────────────────────────────── */
QStatusBar {
    background: #211f1b;
    border-top: 1px solid #3d3830;
    color: #6b6050;
    font-size: 9pt;
}

QStatusBar::item {
    border: none;
}

/* ── Scroll ──────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #332f28;
    border-radius: 4px;
    min-height: 32px;
}

QScrollBar::handle:vertical:hover {
    background: #3d3830;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
}

QScrollBar::handle:horizontal {
    background: #332f28;
    border-radius: 4px;
    min-width: 32px;
}

QScrollBar::handle:horizontal:hover {
    background: #3d3830;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Inputs e campos ─────────────────────────────────────── */
QLineEdit, QSpinBox {
    background: #2a2722;
    border: 1px solid #3d3830;
    border-radius: 5px;
    color: #e8e0d0;
    padding: 3px 8px;
    font-size: 9pt;
    selection-background-color: #6b4e18;
    selection-color: #e8e0d0;
}

QLineEdit:focus, QSpinBox:focus {
    border-color: #6b4e18;
}

QSpinBox::up-button, QSpinBox::down-button {
    width: 0;
    border: none;
}

/* ── Botões ──────────────────────────────────────────────── */
QPushButton {
    background: #2a2722;
    border: 1px solid #3d3830;
    border-radius: 6px;
    color: #a89880;
    padding: 5px 14px;
    font-size: 9pt;
}

QPushButton:hover {
    background: #332f28;
    border-color: #4a4238;
    color: #e8e0d0;
}

QPushButton:pressed {
    background: #1a1814;
}

QPushButton:default, QPushButton[accent="true"] {
    background: #6b4e18;
    border-color: #c8922a;
    color: #e8e0d0;
}

QPushButton:default:hover, QPushButton[accent="true"]:hover {
    background: #7a5a20;
    border-color: #e0a83a;
}

/* ── Menus e dropdowns ───────────────────────────────────── */
QMenu {
    background: #211f1b;
    border: 1px solid #3d3830;
    border-radius: 8px;
    padding: 4px;
    color: #e8e0d0;
    font-size: 9pt;
}

QMenu::item {
    padding: 6px 16px;
    border-radius: 5px;
}

QMenu::item:selected {
    background: #2a2722;
    color: #e8e0d0;
}

QMenu::separator {
    height: 1px;
    background: #3d3830;
    margin: 4px 8px;
}

/* ── Sidebar / TreeView (TOC) ────────────────────────────── */
QTreeView, QListView {
    background: #211f1b;
    border: none;
    color: #a89880;
    font-size: 9pt;
    outline: none;
}

QTreeView::item, QListView::item {
    padding: 4px 8px;
    border-radius: 4px;
}

QTreeView::item:hover, QListView::item:hover {
    background: #2a2722;
    color: #e8e0d0;
}

QTreeView::item:selected, QListView::item:selected {
    background: rgba(200, 146, 42, 0.1);
    color: #c8922a;
    border-left: 2px solid #c8922a;
}

QTreeView::branch {
    background: transparent;
}

/* ── Splitter ────────────────────────────────────────────── */
QSplitter::handle {
    background: #3d3830;
}

QSplitter::handle:horizontal {
    width: 1px;
}

QSplitter::handle:vertical {
    height: 1px;
}

QSplitter::handle:hover {
    background: #c8922a;
}

/* ── Tooltips ────────────────────────────────────────────── */
QToolTip {
    background: #2a2722;
    border: 1px solid #3d3830;
    border-radius: 5px;
    color: #e8e0d0;
    padding: 4px 8px;
    font-size: 9pt;
}

/* ── Dialog / Settings ───────────────────────────────────── */
QLabel {
    color: #a89880;
    font-size: 9pt;
}

QLabel[heading="true"] {
    color: #e8e0d0;
    font-size: 10pt;
}

QCheckBox {
    color: #a89880;
    font-size: 9pt;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3d3830;
    border-radius: 4px;
    background: #2a2722;
}

QCheckBox::indicator:checked {
    background: #c8922a;
    border-color: #c8922a;
}

QCheckBox:hover {
    color: #e8e0d0;
}

QComboBox {
    background: #2a2722;
    border: 1px solid #3d3830;
    border-radius: 5px;
    color: #e8e0d0;
    padding: 4px 10px;
    font-size: 9pt;
}

QComboBox:hover {
    border-color: #4a4238;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background: #211f1b;
    border: 1px solid #3d3830;
    color: #e8e0d0;
    selection-background-color: #2a2722;
    selection-color: #c8922a;
}

/* ── Área do PDF (fundo da rolagem) ──────────────────────── */
QScrollArea {
    background: #1a1814;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: #1a1814;
}
"""


def apply(app):
    """Aplica o tema na QApplication."""
    app.setStyleSheet(STYLESHEET)