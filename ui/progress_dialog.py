from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import Qt


class ProgressDialog(QDialog):
    def __init__(self, total: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("正在识别发票...")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        self._total = total

        layout = QVBoxLayout(self)

        self._file_label = QLabel("准备中...", self)
        self._file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._file_label)

        self._progress = QProgressBar(self)
        self._progress.setRange(0, total)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        self._count_label = QLabel(f"0 / {total}", self)
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._count_label)

        cancel_btn = QPushButton("取消", self)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def update_progress(self, current: int, filename: str) -> None:
        self._progress.setValue(current)
        self._file_label.setText(f"正在处理：{filename}")
        self._count_label.setText(f"{current} / {self._total}")
