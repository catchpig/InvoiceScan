# 设计文档：内联识别进度

**日期：** 2026-05-17
**状态：** 已批准

---

## 需求

将当前识别时弹出的 `ProgressDialog` 模态窗口，改为在文件列表每一行右侧内联显示识别状态文字，让用户在识别过程中仍可操作主窗口。

---

## 交互设计

### 文件列表行布局

每行使用自定义 widget，左右两个 `QLabel`：

| 左侧 | 右侧状态文字 | 颜色 |
|------|------------|------|
| `○ invoice.pdf` | 等待 | 灰色 |
| `… invoice.pdf` | 识别中 | 蓝色 |
| `✓ invoice.pdf` | 完成 | 绿色 |
| `⚠ invoice.pdf` | 需复核 | 橙色 |
| `✗ invoice.pdf` | 失败 | 红色 |

### 取消按钮

- 工具栏新增"取消识别"按钮（`QAction`）
- 默认隐藏，点击"开始识别"后显示，OCR 完成后隐藏
- 点击后调用 `_worker.cancel()`

### 模型加载阶段

忽略加载阶段进度提示，直到第一个文件开始处理时文件列表才更新状态。

---

## 实现范围

### `ui/main_window.py`

1. 新增 `_FileListItem(QWidget)` 类
   - `QHBoxLayout`：左 `QLabel`（图标+文件名），右 `QLabel`（状态文字）
   - `update(icon, filename, status_text, color)` 方法
2. `_add_files`：改为创建 `QListWidgetItem` + `setItemWidget(_FileListItem(...))`
3. `_on_ocr_progress`：调用对应行的 `_FileListItem.update()` 更新为"识别中"
4. `_on_invoice_done`：调用对应行的 `_FileListItem.update()` 更新为最终状态
5. `_on_invoice_changed`：同上，更新行显示
6. 工具栏添加 `_cancel_act`，默认 `setVisible(False)`
7. `_on_start_ocr`：移除 `ProgressDialog`，改为显示 `_cancel_act`
8. `_on_ocr_finished`：隐藏 `_cancel_act`

### `ui/progress_dialog.py`

整个文件删除。

### `_on_model_status` / `model_status` 信号

`_OcrWorker.model_status` 信号及 `_on_model_status` 回调不再需要，可一并移除。

---

## 不变部分

- `_OcrWorker` 的核心识别逻辑
- `_on_export`、`PreviewPanel`、状态栏统计逻辑
- 重复发票检测弹窗
