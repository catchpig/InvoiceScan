# 内联识别进度 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移除 ProgressDialog 弹窗，改为在文件列表每行右侧内联显示识别状态文字，工具栏添加可隐藏的取消按钮。

**Architecture:** 新增 `_FileListItem` widget 替代原有 `QListWidgetItem` 文字更新方式；`MainWindow` 维护一个 `_item_widgets` 列表用于按行索引快速更新状态；取消按钮作为 `QAction` 挂在工具栏，默认隐藏，识别期间可见。

**Tech Stack:** Python 3.14, PyQt6, pytest

---

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `ui/main_window.py` | 新增 `_STATUS_LABELS`、`_FileListItem`；改造文件列表和 OCR 流程 |
| 删除 | `ui/progress_dialog.py` | 整个文件不再需要 |
| 修改 | `tests/test_main_window.py` | 新增 `_STATUS_LABELS` 覆盖测试 |

---

### Task 1: 添加 `_STATUS_LABELS` 数据并测试

**Files:**
- Modify: `ui/main_window.py`
- Modify: `tests/test_main_window.py`

- [ ] **Step 1: 在 `main_window.py` 的 `_STATUS_ICONS` 定义之后添加 `_STATUS_LABELS`**

在 `_STATUS_ICONS` 字典后紧接着添加：

```python
_STATUS_LABELS: dict[str, tuple[str, str]] = {
    InvoiceStatus.PENDING:    ("等待",   "#888888"),
    InvoiceStatus.PROCESSING: ("识别中", "#4a9eff"),
    InvoiceStatus.SUCCESS:    ("完成",   "#4caf50"),
    InvoiceStatus.REVIEW:     ("需复核", "#ff9800"),
    InvoiceStatus.FAILED:     ("失败",   "#f44336"),
}
```

- [ ] **Step 2: 在 `tests/test_main_window.py` 中写入以下测试**

```python
def test_status_labels_covers_all_statuses():
    from ui.main_window import _STATUS_LABELS
    for status in [
        InvoiceStatus.PENDING, InvoiceStatus.PROCESSING,
        InvoiceStatus.SUCCESS, InvoiceStatus.REVIEW, InvoiceStatus.FAILED,
    ]:
        assert status in _STATUS_LABELS, f"缺少状态: {status}"
        text, color = _STATUS_LABELS[status]
        assert text, f"{status} 的文字为空"
        assert color.startswith("#"), f"{status} 的颜色格式错误: {color}"


def test_status_labels_text_values():
    from ui.main_window import _STATUS_LABELS
    assert _STATUS_LABELS[InvoiceStatus.PENDING][0]    == "等待"
    assert _STATUS_LABELS[InvoiceStatus.PROCESSING][0] == "识别中"
    assert _STATUS_LABELS[InvoiceStatus.SUCCESS][0]    == "完成"
    assert _STATUS_LABELS[InvoiceStatus.REVIEW][0]     == "需复核"
    assert _STATUS_LABELS[InvoiceStatus.FAILED][0]     == "失败"
```

- [ ] **Step 3: 运行测试，确认通过**

```
cd D:\android\InvoiceScan
.venv\Scripts\pytest tests/test_main_window.py -v
```

预期：所有测试 PASS。

- [ ] **Step 4: 提交**

```
git add ui/main_window.py tests/test_main_window.py
git commit -m "feat: add _STATUS_LABELS for inline progress display"
```

---

### Task 2: 实现 `_FileListItem` widget 类

**Files:**
- Modify: `ui/main_window.py`（在 `_STATUS_LABELS` 之后、`_OcrWorker` 之前插入）

- [ ] **Step 1: 在 `main_window.py` 中添加所需 import**

在文件顶部 `from PyQt6.QtWidgets import (...)` 中添加 `QWidget`、`QHBoxLayout`、`QLabel`（若尚未有）：

```python
from PyQt6.QtWidgets import (
    QMainWindow, QListWidget, QListWidgetItem, QToolBar,
    QStatusBar, QFileDialog, QMessageBox, QSplitter, QLabel,
    QWidget, QHBoxLayout,
)
```

- [ ] **Step 2: 在 `_STATUS_LABELS` 字典之后插入 `_FileListItem` 类**

```python
class _FileListItem(QWidget):
    def __init__(self, filename: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        self._name_label = QLabel(self)
        self._status_label = QLabel(self)
        layout.addWidget(self._name_label)
        layout.addStretch()
        layout.addWidget(self._status_label)
        self.update_status(filename, InvoiceStatus.PENDING)

    def update_status(self, filename: str, status: str) -> None:
        icon = _STATUS_ICONS.get(status, "○")
        self._name_label.setText(f"{icon} {filename}")
        text, color = _STATUS_LABELS.get(status, ("", "#888888"))
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color};")
```

- [ ] **Step 3: 运行现有测试，确保无回归**

```
.venv\Scripts\pytest tests/test_main_window.py -v
```

预期：所有测试 PASS。

- [ ] **Step 4: 提交**

```
git add ui/main_window.py
git commit -m "feat: add _FileListItem widget for inline status display"
```

---

### Task 3: 将文件列表改为使用 `_FileListItem`

**Files:**
- Modify: `ui/main_window.py`

- [ ] **Step 1: 在 `MainWindow.__init__` 中初始化 `_item_widgets`**

在 `self._invoices: list[Invoice] = []` 下方添加：

```python
self._item_widgets: list[_FileListItem] = []
```

- [ ] **Step 2: 替换 `_add_files` 方法**

```python
def _add_files(self, paths: list[str]) -> None:
    existing = set(self._file_paths)
    for path in paths:
        if path not in existing:
            self._file_paths.append(path)
            self._invoices.append(Invoice(source_file=os.path.basename(path)))
            filename = os.path.basename(path)
            item = QListWidgetItem()
            widget = _FileListItem(filename)
            item.setSizeHint(widget.sizeHint())
            self._file_list.addItem(item)
            self._file_list.setItemWidget(item, widget)
            self._item_widgets.append(widget)
    self._update_stats()
```

- [ ] **Step 3: 替换 `_on_clear` 方法**

```python
def _on_clear(self) -> None:
    self._file_paths.clear()
    self._invoices.clear()
    self._item_widgets.clear()
    self._file_list.clear()
    self._preview.clear()
    self._update_stats()
```

- [ ] **Step 4: 替换 `_on_ocr_progress` 方法**

```python
def _on_ocr_progress(self, current: int, filename: str) -> None:
    row = current - 1
    if 0 <= row < len(self._item_widgets):
        self._item_widgets[row].update_status(filename, InvoiceStatus.PROCESSING)
```

- [ ] **Step 5: 替换 `_on_invoice_done` 方法**

```python
def _on_invoice_done(self, row: int, invoice: Invoice) -> None:
    self._invoices[row] = invoice
    if 0 <= row < len(self._item_widgets):
        self._item_widgets[row].update_status(invoice.source_file, invoice.status)
    if self._file_list.currentRow() == row:
        self._preview.show_invoice(invoice)
    self._update_stats()
```

- [ ] **Step 6: 替换 `_on_invoice_changed` 方法**

```python
def _on_invoice_changed(self, invoice: Invoice) -> None:
    row = self._file_list.currentRow()
    if 0 <= row < len(self._invoices):
        self._invoices[row] = invoice
        self._item_widgets[row].update_status(invoice.source_file, invoice.status)
```

- [ ] **Step 7: 运行测试**

```
.venv\Scripts\pytest tests/test_main_window.py -v
```

预期：所有测试 PASS。

- [ ] **Step 8: 提交**

```
git add ui/main_window.py
git commit -m "feat: replace QListWidgetItem text with _FileListItem widgets"
```

---

### Task 4: 添加取消按钮，移除 ProgressDialog

**Files:**
- Modify: `ui/main_window.py`
- Delete: `ui/progress_dialog.py`

- [ ] **Step 1: 在 `_setup_ui` 的工具栏部分添加取消按钮**

在 `start_act` 添加之后插入：

```python
self._cancel_act = QAction("取消识别", self)
self._cancel_act.triggered.connect(self._on_cancel)
self._cancel_act.setVisible(False)
toolbar.addAction(self._cancel_act)
```

- [ ] **Step 2: 新增 `_on_cancel` 方法**

在 `_on_start_ocr` 之前插入：

```python
def _on_cancel(self) -> None:
    if hasattr(self, "_worker"):
        self._worker.cancel()
```

- [ ] **Step 3: 替换 `_on_start_ocr` 方法**

```python
def _on_start_ocr(self) -> None:
    if not self._file_paths:
        QMessageBox.information(self, "提示", "请先添加发票文件")
        return
    self._cancel_act.setVisible(True)
    self._worker = _OcrWorker(self._file_paths)
    self._thread = QThread()
    self._worker.moveToThread(self._thread)
    self._thread.started.connect(self._worker.run)
    self._worker.progress.connect(self._on_ocr_progress)
    self._worker.invoice_done.connect(self._on_invoice_done)
    self._worker.finished.connect(self._on_ocr_finished)
    self._thread.start()
```

- [ ] **Step 4: 替换 `_on_ocr_finished` 方法**

```python
def _on_ocr_finished(self) -> None:
    logging.info("_on_ocr_finished: start")
    self._thread.quit()
    logging.info("_on_ocr_finished: after quit")
    self._thread.wait(3000)
    logging.info("_on_ocr_finished: after wait")
    self._cancel_act.setVisible(False)
    self._update_stats()
    logging.info("_on_ocr_finished: after update_stats")
    duplicates = _find_duplicates(self._invoices)
    if duplicates:
        msg = "检测到重复发票：\n" + "\n".join(
            f"发票代码 {code}  号码 {num}" for code, num in duplicates
        )
        QMessageBox.warning(self, "重复发票提示", msg)
```

- [ ] **Step 5: 删除 `_on_model_status` 方法**

从 `MainWindow` 中完整移除：

```python
def _on_model_status(self, message: str) -> None:
    if message:
        self._progress_dlg.set_loading_model(message)
    else:
        self._progress_dlg.set_processing()
```

- [ ] **Step 6: 移除 `_OcrWorker` 中的 `model_status` 信号**

在 `_OcrWorker` 类中删除这一行：

```python
model_status = pyqtSignal(str)
```

以及 `run` 方法中的这一行：

```python
self.model_status.emit("")  # 初始化完成，切换到文件处理模式
```

- [ ] **Step 7: 移除 `main_window.py` 顶部的 ProgressDialog import**

删除：

```python
from ui.progress_dialog import ProgressDialog
```

- [ ] **Step 8: 删除 `progress_dialog.py`**

```
git rm ui/progress_dialog.py
```

- [ ] **Step 9: 运行测试**

```
.venv\Scripts\pytest tests/ -v
```

预期：所有测试 PASS，无 import 错误。

- [ ] **Step 10: 提交**

```
git add ui/main_window.py
git commit -m "feat: remove ProgressDialog, add inline cancel action"
```
