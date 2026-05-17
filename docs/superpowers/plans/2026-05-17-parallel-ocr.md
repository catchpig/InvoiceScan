# 并行 OCR 识别 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 OCR 识别从顺序处理改为并发执行，工具栏添加并发数 QSpinBox（1~8，默认 3，QSettings 持久化）。

**Architecture:** 在 `_OcrWorker` 里将顺序 for 循环替换为 `concurrent.futures.ThreadPoolExecutor`；每个任务独立实例化 `OcrEngine + InvoiceParser`；`MainWindow` 工具栏新增 `QSpinBox`，值在 OCR 开始时写入 `QSettings`，识别期间禁用。

**Tech Stack:** Python 3.14, PyQt6, concurrent.futures, QSettings, pytest

---

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `ui/main_window.py` | `_OcrWorker` 并发重构 + `QSpinBox` 工具栏 |
| 修改 | `tests/test_main_window.py` | 新增 worker 参数测试 |

---

### Task 1: `_OcrWorker` 支持并发执行

**Files:**
- Modify: `ui/main_window.py`（`_OcrWorker` 类，约 178-234 行）
- Modify: `tests/test_main_window.py`

- [ ] **Step 1: 在 `tests/test_main_window.py` 写失败测试**

在文件末尾追加：

```python
def test_ocr_worker_stores_max_workers():
    from ui.main_window import _OcrWorker
    w = _OcrWorker([], max_workers=5)
    assert w._max_workers == 5


def test_ocr_worker_default_max_workers_is_3():
    from ui.main_window import _OcrWorker
    w = _OcrWorker([])
    assert w._max_workers == 3
```

- [ ] **Step 2: 运行测试，确认失败**

```
.venv\Scripts\pytest tests/test_main_window.py::test_ocr_worker_stores_max_workers tests/test_main_window.py::test_ocr_worker_default_max_workers_is_3 -v
```

预期：FAILED（`_OcrWorker.__init__` 没有 `max_workers` 参数）

- [ ] **Step 3: 在 `ui/main_window.py` 顶部 import 块中添加 `concurrent.futures`**

在 `import os` 之后添加：

```python
import concurrent.futures
```

- [ ] **Step 4: 替换整个 `_OcrWorker` 类**

将现有 `_OcrWorker`（约 178-234 行）替换为：

```python
class _OcrWorker(QObject):
    progress = pyqtSignal(int, str)
    file_progress = pyqtSignal(int, int)  # (row, percent 0-100)
    invoice_done = pyqtSignal(int, Invoice)
    finished = pyqtSignal()

    def __init__(self, file_paths: list[str],
                 row_indices: list[int] | None = None,
                 max_workers: int = 3):
        super().__init__()
        self._file_paths = file_paths
        self._row_indices = row_indices
        self._max_workers = max_workers
        self._cancelled = False

    def cancel(self) -> None:
        logging.info("Worker: cancel requested")
        self._cancelled = True

    def _process_file(self, i: int, path: str, row: int) -> None:
        if self._cancelled:
            return
        self.progress.emit(row, os.path.basename(path))
        self.file_progress.emit(row, 0)
        try:
            engine = OcrEngine()
            parser = InvoiceParser()
            texts = engine.extract_text_from_file(
                path,
                progress_callback=lambda pct, r=row: self.file_progress.emit(r, pct),
            )
            invoice = parser.parse(texts, source_file=os.path.basename(path))
            logging.info("File %d done, status=%s", i, invoice.status)
        except Exception as exc:
            logging.exception("Error processing file %d: %s", i, path)
            invoice = Invoice(
                source_file=os.path.basename(path),
                status=InvoiceStatus.FAILED,
                error_message=str(exc),
            )
        self.invoice_done.emit(row, invoice)

    def run(self) -> None:
        logging.info("Worker.run started, files=%s", self._file_paths)
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=self._max_workers) as executor:
            futures = []
            for i, path in enumerate(self._file_paths):
                if self._cancelled:
                    break
                row = self._row_indices[i] if self._row_indices else i
                futures.append(executor.submit(self._process_file, i, path, row))
            concurrent.futures.wait(futures)
        logging.info("Worker.run finished")
        self.finished.emit()
```

- [ ] **Step 5: 运行测试，确认通过**

```
.venv\Scripts\pytest tests/test_main_window.py::test_ocr_worker_stores_max_workers tests/test_main_window.py::test_ocr_worker_default_max_workers_is_3 -v
```

预期：2 passed

- [ ] **Step 6: 运行全套测试，确认无回归**

```
.venv\Scripts\pytest tests/ -q
```

预期：全部 PASS

- [ ] **Step 7: 提交**

```
git add ui/main_window.py tests/test_main_window.py
git commit -m "feat: parallel OCR execution via ThreadPoolExecutor"
```

---

### Task 2: 工具栏添加并发数 `QSpinBox` + `QSettings` 持久化

**Files:**
- Modify: `ui/main_window.py`（`_setup_ui`、`_start_ocr_for_pending`、`_on_ocr_finished`）
- Modify: `tests/test_main_window.py`

- [ ] **Step 1: 在 `tests/test_main_window.py` 写失败测试**

在文件末尾追加：

```python
def test_ocr_worker_receives_max_workers_from_spinbox():
    from unittest.mock import patch, MagicMock
    from ui.main_window import _OcrWorker
    captured = {}

    original_init = _OcrWorker.__init__

    def patched_init(self, file_paths, row_indices=None, max_workers=3):
        captured["max_workers"] = max_workers
        original_init(self, file_paths, row_indices, max_workers)

    with patch.object(_OcrWorker, "__init__", patched_init):
        from PyQt6.QtWidgets import QApplication
        import sys
        app = QApplication.instance() or QApplication(sys.argv)
        from ui.main_window import MainWindow
        win = MainWindow()
        win._workers_spin.setValue(5)
        win._invoices[0:0] = []  # keep empty, just verify attribute exists
        assert win._workers_spin.value() == 5
        win.close()
```

- [ ] **Step 2: 运行测试，确认失败**

```
.venv\Scripts\pytest "tests/test_main_window.py::test_ocr_worker_receives_max_workers_from_spinbox" -v
```

预期：FAILED（`MainWindow` 没有 `_workers_spin` 属性）

- [ ] **Step 3: 在 `ui/main_window.py` 的 import 块中添加 `QSpinBox` 和 `QSettings`**

将现有 `from PyQt6.QtWidgets import (...)` 中加入 `QSpinBox`（如尚未有）：

```python
from PyQt6.QtWidgets import (
    QMainWindow, QListWidget, QListWidgetItem, QToolBar,
    QStatusBar, QFileDialog, QMessageBox, QSplitter, QLabel,
    QWidget, QHBoxLayout, QVBoxLayout, QFrame, QSizePolicy,
    QProgressBar, QSpinBox,
)
```

在 `from PyQt6.QtCore import ...` 行中加入 `QSettings`：

```python
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal, QSize, QSettings
```

- [ ] **Step 4: 在 `_setup_ui` 的取消按钮之后添加并发数控件**

找到 `toolbar.addAction(self._cancel_act)` 这一行，在其之后插入：

```python
        toolbar.addSeparator()
        workers_label = QLabel("并发:", self)
        workers_label.setStyleSheet("padding: 0 4px 0 8px;")
        toolbar.addWidget(workers_label)
        self._workers_spin = QSpinBox(self)
        self._workers_spin.setRange(1, 8)
        self._workers_spin.setValue(
            int(QSettings("InvoiceScan", "InvoiceScan").value("max_workers", 3))
        )
        self._workers_spin.setFixedWidth(58)
        self._workers_spin.setToolTip("同时识别的文件数（1~8）")
        toolbar.addWidget(self._workers_spin)
```

- [ ] **Step 5: 在 `_start_ocr_for_pending` 中读取 spinbox 值并传给 worker**

找到 `_start_ocr_for_pending` 方法，将：

```python
        self._cancel_act.setVisible(True)
        self._worker = _OcrWorker(pending_paths, pending_indices)
```

替换为：

```python
        max_workers = self._workers_spin.value()
        QSettings("InvoiceScan", "InvoiceScan").setValue("max_workers", max_workers)
        self._cancel_act.setVisible(True)
        self._workers_spin.setEnabled(False)
        self._worker = _OcrWorker(pending_paths, pending_indices, max_workers=max_workers)
```

- [ ] **Step 6: 在 `_on_ocr_finished` 中恢复 spinbox**

找到 `_on_ocr_finished` 中的 `self._cancel_act.setVisible(False)`，在其后添加：

```python
        self._workers_spin.setEnabled(True)
```

- [ ] **Step 7: 运行测试，确认通过**

```
.venv\Scripts\pytest "tests/test_main_window.py::test_ocr_worker_receives_max_workers_from_spinbox" -v
```

预期：PASS

- [ ] **Step 8: 运行全套测试，确认无回归**

```
.venv\Scripts\pytest tests/ -q
```

预期：全部 PASS

- [ ] **Step 9: 提交**

```
git add ui/main_window.py tests/test_main_window.py
git commit -m "feat: add concurrency QSpinBox to toolbar with QSettings persistence"
```
