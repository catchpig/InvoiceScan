# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git 规则

- 创建或修改任何文件后，**立即执行 `git add <文件路径>`**
- **禁止执行 `git commit`**，不论任何情况

## 常用命令

```bash
# 运行应用
python main.py

# 运行全部测试
python -m pytest tests/

# 运行单个测试文件
python -m pytest tests/test_exporter.py -v

# 运行单个测试函数
python -m pytest tests/test_exporter.py::test_export_skips_non_success_invoices

# 打包 exe（输出到 dist/发票扫描识别系统/）
pyinstaller 发票扫描识别系统.spec
```

## 架构概览

### 数据流

```
文件拖入/选择
    → MainWindow._add_files()
    → _OcrWorker（QThread + ThreadPoolExecutor）
        → OcrEngine.extract_text_from_file()  → list[str]
        → InvoiceParser.parse(texts)           → Invoice
    → MainWindow._invoices[row] = invoice
    → 导出时 Exporter.export(invoices)         → .xlsx
```

### 核心层

**`models/invoice.py`** — 唯一数据模型。`Invoice` 是普通 dataclass，`InvoiceStatus` 是普通类（非 Enum），值为字符串常量（`"pending"` / `"processing"` / `"success"` / `"review"` / `"failed"`）。

**`core/ocr_engine.py`** — 图像识别。对每张图像执行**两次 OCR**：
- Standard pass（对比度+锐化）：金额、税号等数字字段准确率高
- CLAHE pass（4× 放大 + CLAHE 均衡化）：企业名称字符准确率更高

两路结果合并时仅保留 CLAHE 中含"有限"/"公司"/"贸易"/"企业"的文本行，追加到 standard 结果前。PDF 转图像依赖 bundled poppler（`poppler/poppler-24.08.0/Library/bin/`），PDF 识别在找到"发票代码"+"发票号码"后提前终止。

**`core/invoice_parser.py`** — 纯正则解析。`_normalize_text` 先修正 OCR 常见误读（年份 `?026→2026`、`Y/X→¥` 等），再逐字段提取。`_determine_status` 判断：缺少任意必填字段（`invoice_number/date/buyer_name/seller_name`）→ REVIEW；金额不平衡（误差>0.01）→ REVIEW；否则 SUCCESS。

**`core/exporter.py`** — Excel 导出。`export()` 入口先**过滤仅 SUCCESS**，再去重（保留同一发票代码+号码的最后一条），写入 xlsx。汇总模式（每票一行）与明细模式（每条货物明细一行）通过 `ExportMode` 枚举切换。

### UI 层

**`ui/main_window.py`** — 主窗口。左侧文件列表 + 右侧 PreviewPanel，`QSplitter` 分割。`_OcrWorker` 继承 `QObject`，`moveToThread` 到 `QThread`，通过信号（`invoice_done`/`file_progress`）回调主线程更新 UI。并发数通过 `QSpinBox`（1~8）控制，持久化到 `QSettings("InvoiceScan", "InvoiceScan")`。

**`ui/preview_panel.py`** — 发票详情面板。字段分四组（`_FIELD_LABELS` / `_BUYER_FIELDS` / `_SELLER_FIELDS` / `_AMOUNT_FIELDS`）渲染为 `QFormLayout`，保存时将文本写回 `Invoice` 对象并 emit `invoice_changed` 信号。`_DECIMAL_FIELDS` 集合控制哪些字段做 Decimal 转换。

**`ui/theme.py`** — 全局样式。`COLORS` dict 集中管理所有颜色 token，`STYLESHEET` 为完整 QSS 字符串，在 `main.py` 中通过 `app.setStyleSheet(STYLESHEET)` 全局应用。

### 关键约束

- `InvoiceStatus` 不是 Enum，比较用字符串：`inv.status == InvoiceStatus.SUCCESS`（即 `== "success"`）
- 导出只包含 `SUCCESS` 状态的发票（非 SUCCESS 在 `Exporter.export()` 入口被过滤）
- Poppler 必须位于 `poppler/poppler-24.08.0/Library/bin/pdftoppm.exe`，否则 PDF 识别失败
- 打包 spec 中 `excludes` 了 torch/easyocr/scipy 等大依赖以控制体积
