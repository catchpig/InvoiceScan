# 设计文档：并行 OCR 识别

**日期：** 2026-05-17  
**状态：** 已批准

---

## 需求

将当前顺序执行的 OCR 识别改为并发执行，允许同时处理多张发票，提升批量识别吞吐量。并发数由用户在工具栏设置（1~8），持久化保存。

---

## 实现范围

### `ui/main_window.py`

1. `_OcrWorker.__init__` 新增 `max_workers: int` 参数（默认 3）
2. `_OcrWorker.run()` 用 `concurrent.futures.ThreadPoolExecutor(max_workers)` 替代顺序 for 循环：
   - 每个任务独立创建 `OcrEngine` + `InvoiceParser` 实例（不跨线程共享）
   - 任务启动前检查 `_cancelled`，已取消则不提交新任务
   - `progress`、`invoice_done` 信号从线程池子线程 emit，PyQt6 通过队列连接安全传递到主线程
3. `_setup_ui` 工具栏新增：
   - `QLabel("并发:")` + `QSpinBox`（范围 1~8，初始值从 `QSettings` 读取，默认 3）
   - spinbox 存为 `self._workers_spin`
   - 识别期间 `self._workers_spin.setEnabled(False)`，完成后恢复
4. `_on_start_ocr` 把 `self._workers_spin.value()` 传入 `_OcrWorker`，并在 `QSettings` 写入当前值
5. `_on_ocr_finished` 调用 `self._workers_spin.setEnabled(True)`

### 不变部分

- `OcrEngine`、`InvoiceParser`、`_FileListItem`、`PreviewPanel`、导出逻辑
- 取消按钮、信号连接、`_on_ocr_progress`、`_on_invoice_done`、`_on_ocr_finished` 的其余逻辑

---

## 并发数选择说明

| 并发数 | 适用场景 |
|--------|---------|
| 1 | 低内存机器或调试 |
| 3（默认）| 8 核机器日常使用，平衡速度与内存 |
| 8 | 高性能机器大批量任务 |

每个并发任务独立加载 RapidOCR 模型（约 200 MB），用户根据可用内存自行调整。

---

## 线程安全

- `OcrEngine` 和 `InvoiceParser` 每个任务独立实例化，无共享状态
- PyQt6 跨线程信号通过内部队列传递，emit 无需额外加锁
- `_cancelled` 标志只用于读（子线程只读取，主线程只写入），Python 的 GIL 保证赋值原子性

---

## 不变的用户体验

- 文件列表各行仍实时显示状态（等待 → 识别中 → 完成/失败），多行可同时变更
- 取消按钮行为不变：设置 `_cancelled = True`，已在运行的任务跑完后不再提交新任务
- 识别完成后仍触发重复发票检测弹窗
