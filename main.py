import os
# 在 ONNX/numpy/OpenBLAS 导入前限制每个引擎实例使用的线程数
# 3 并发任务 × 2 线程 ≈ 6 线程，CPU 占用可控在 70% 左右
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
os.environ.setdefault('MKL_NUM_THREADS', '2')

import sys
import traceback
import logging

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
