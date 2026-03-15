import sys
from PySide6.QtWidgets import QApplication
from app import App


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("PyReaderPDF")

    # Estilo base escuro — será refinado na Fase 1
    app.setStyleSheet("""
        QWidget {
            background-color: #1e1e1e;
            color: #e0e0e0;
            font-family: Arial;
            font-size: 10pt;
        }
        QMainWindow {
            background-color: #1e1e1e;
        }
    """)

    window = App()
    window.show()
    sys.exit(app.exec())