import sys
from PySide6.QtWidgets import QApplication
from app import App
from core.theme import apply as apply_theme

if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_theme(app)
    app.setApplicationName("PyReaderPDF")
    window = App()
    window.show()
    sys.exit(app.exec())