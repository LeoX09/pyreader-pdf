import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from qfluentwidgets import setTheme, Theme

from app import App


if __name__ == "__main__":
    # HiDPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("PyReaderPDF")

    # Fluent Dark Theme
    setTheme(Theme.DARK)

    window = App()
    window.show()
    sys.exit(app.exec())