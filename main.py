import sys
import traceback
import logging
import os

_log_fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.DEBUG)
_console_handler.setFormatter(_log_fmt)

logging.basicConfig(level=logging.DEBUG, handlers=[_console_handler])

def _excepthook(exc_type, exc_value, exc_tb):
    msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.critical("Unhandled exception:\n%s", msg)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _excepthook

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.theme import STYLESHEET


def main() -> None:
    logging.info("App starting")
    app = QApplication(sys.argv)
    app.setApplicationName("发票扫描识别系统")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    logging.info("Main window shown")
    code = app.exec()
    logging.info("App exiting with code %d", code)
    sys.exit(code)


if __name__ == "__main__":
    main()
