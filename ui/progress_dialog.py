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

        self._file_label = QLabel("正在初始化OCR引擎，请稍候...", self)
        self._file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_label.setWordWrap(True)
        layout.addWidget(self._file_label)

        self._progress = QProgressBar(self)
        self._progress.setRange(0, 0)   # 默认不定进度条（模型初始化阶段）
        layout.addWidget(self._progress)

        self._count_label = QLabel("", self)
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._count_label)

        cancel_btn = QPushButton("取消", self)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def set_loading_model(self, message: str) -> None:
        """切换到模型加载阶段：不定进度条 + 状态文字。"""
        self._progress.setRange(0, 0)
        self._file_label.setText(message)
        self._count_label.setText("")

    def set_processing(self) -> None:
        """切换回文件处理阶段：恢复确定进度条。"""
        self._progress.setRange(0, self._total)
        self._progress.setValue(0)
        self._count_label.setText(f"0 / {self._total}")

    def update_progress(self, current: int, filename: str) -> None:
        self._progress.setValue(current)
        self._file_label.setText(f"正在处理：{filename}")
        self._count_label.setText(f"{current} / {self._total}")
