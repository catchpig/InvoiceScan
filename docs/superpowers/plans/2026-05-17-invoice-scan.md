# InvoiceScan 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 构建一个 Windows 桌面应用，支持批量导入 PDF/PNG 中国增值税发票，通过本地 PaddleOCR 提取结构化字段，支持预览编辑，导出 Excel。

**架构：** 分三层 — 数据模型层（models）→ 核心处理层（OCR 引擎、解析器、导出器）→ PyQt6 UI 层。OCR 引擎将 PDF/PNG 统一转换为文本列表；发票解析器通过正则从文本提取结构化字段；UI 在 QThread 后台执行 OCR 任务以保持界面响应。

**技术栈：** Python 3.9+, PyQt6, PaddleOCR (paddlepaddle), pdf2image + poppler, openpyxl, pytest

---

## 文件结构

```
InvoiceScan/
├── main.py                     # QApplication 入口
├── requirements.txt            # 所有 Python 依赖
├── models/
│   ├── __init__.py
│   └── invoice.py              # Invoice + InvoiceItem dataclass，InvoiceStatus 常量
├── core/
│   ├── __init__.py
│   ├── ocr_engine.py           # PaddleOCR 封装：PDF/PNG → list[str]
│   ├── invoice_parser.py       # OCR 文本 → Invoice dataclass（正则提取）
│   └── exporter.py             # Invoice 列表 → Excel（汇总/明细两种模式）
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # 主窗口：文件列表 + 工具栏 + 状态栏 + QThread 工作者
│   ├── preview_panel.py        # 右侧面板：字段展示与编辑表单
│   └── progress_dialog.py      # 批量处理进度弹窗
└── tests/
    ├── __init__.py
    ├── test_invoice_model.py
    ├── test_ocr_engine.py
    ├── test_invoice_parser.py
    ├── test_exporter.py
    └── test_main_window.py
```

---

## Task 1：项目初始化

**文件：**
- 创建：`requirements.txt`
- 创建：`models/__init__.py`、`core/__init__.py`、`ui/__init__.py`、`tests/__init__.py`

- [ ] **步骤 1：创建 requirements.txt**

```
PyQt6>=6.6.0
paddlepaddle==2.6.1
paddleocr>=2.7.0
pdf2image>=1.16.3
Pillow>=10.0.0
openpyxl>=3.1.2
pytest>=7.4.0
pytest-cov>=4.1.0
```

- [ ] **步骤 2：创建各包 `__init__.py`（均为空文件）**

```
models/__init__.py
core/__init__.py
ui/__init__.py
tests/__init__.py
```

- [ ] **步骤 3：安装依赖**

```bash
pip install PyQt6 openpyxl pdf2image Pillow pytest pytest-cov
```

PaddlePaddle（CPU 版）单独安装：
```bash
pip install paddlepaddle -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install paddleocr
```

- [ ] **步骤 4：验证 PaddleOCR 可用**

```python
# 在 Python REPL 中验证
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='ch')
print("PaddleOCR OK")
```

期望输出：`PaddleOCR OK`（首次运行会下载模型文件，需联网）

- [ ] **步骤 5：提交**

```bash
git init
git add requirements.txt models/__init__.py core/__init__.py ui/__init__.py tests/__init__.py
git commit -m "chore: project setup with requirements and package structure"
```

---

## Task 2：发票数据模型

**文件：**
- 创建：`models/invoice.py`
- 创建：`tests/test_invoice_model.py`

- [ ] **步骤 1：编写失败测试**

```python
# tests/test_invoice_model.py
from decimal import Decimal
from models.invoice import Invoice, InvoiceItem, InvoiceStatus


def test_invoice_item_creation():
    item = InvoiceItem(name="服务费", quantity="1", unit_price=Decimal("1000.00"), amount=Decimal("1000.00"))
    assert item.name == "服务费"
    assert item.amount == Decimal("1000.00")


def test_invoice_creation_defaults():
    inv = Invoice(source_file="test.pdf")
    assert inv.source_file == "test.pdf"
    assert inv.status == InvoiceStatus.PENDING
    assert inv.items == []
    assert inv.subtotal == Decimal("0")
    assert inv.error_message == ""


def test_invoice_status_constants():
    assert InvoiceStatus.SUCCESS == "success"
    assert InvoiceStatus.REVIEW == "review"
    assert InvoiceStatus.FAILED == "failed"
    assert InvoiceStatus.PENDING == "pending"
    assert InvoiceStatus.PROCESSING == "processing"


def test_invoice_fields_present():
    inv = Invoice(
        source_file="test.pdf",
        invoice_code="044001900111",
        invoice_number="12345678",
        invoice_date="2024-03-15",
        buyer_name="XX科技",
        buyer_tax_id="91440300XXXX",
        seller_name="YY贸易",
        seller_tax_id="91440100YYYY",
        subtotal=Decimal("1000.00"),
        tax_rate="13%",
        tax_amount=Decimal("130.00"),
        total_amount=Decimal("1130.00"),
        issuer="张三",
        invoice_type="增值税专用发票",
    )
    assert inv.invoice_code == "044001900111"
    assert inv.total_amount == Decimal("1130.00")
```

- [ ] **步骤 2：运行测试，确认失败**

```bash
pytest tests/test_invoice_model.py -v
```

期望：`ModuleNotFoundError: No module named 'models.invoice'`

- [ ] **步骤 3：实现 Invoice 数据模型**

```python
# models/invoice.py
from dataclasses import dataclass, field
from decimal import Decimal


class InvoiceStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    REVIEW = "review"
    FAILED = "failed"


@dataclass
class InvoiceItem:
    name: str = ""
    quantity: str = ""
    unit_price: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")


@dataclass
class Invoice:
    source_file: str = ""
    invoice_code: str = ""
    invoice_number: str = ""
    invoice_date: str = ""
    buyer_name: str = ""
    buyer_tax_id: str = ""
    seller_name: str = ""
    seller_tax_id: str = ""
    items: list = field(default_factory=list)
    subtotal: Decimal = Decimal("0")
    tax_rate: str = ""
    tax_amount: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    issuer: str = ""
    invoice_type: str = ""
    status: str = InvoiceStatus.PENDING
    error_message: str = ""
```

- [ ] **步骤 4：运行测试，确认通过**

```bash
pytest tests/test_invoice_model.py -v
```

期望：4 个测试全部 PASS

- [ ] **步骤 5：提交**

```bash
git add models/invoice.py tests/test_invoice_model.py
git commit -m "feat: add Invoice and InvoiceItem data models"
```

---

## Task 3：OCR 引擎

**文件：**
- 创建：`core/ocr_engine.py`
- 创建：`tests/test_ocr_engine.py`

- [ ] **步骤 1：编写失败测试**

```python
# tests/test_ocr_engine.py
import os
import pytest
from unittest.mock import patch, MagicMock
from core.ocr_engine import OcrEngine


def test_ocr_engine_initializes():
    with patch('core.ocr_engine.PaddleOCR') as mock_paddle:
        engine = OcrEngine()
        mock_paddle.assert_called_once_with(use_angle_cls=True, lang='ch')


def test_extract_text_from_image_returns_list_of_strings():
    with patch('core.ocr_engine.PaddleOCR') as mock_paddle:
        mock_ocr = MagicMock()
        mock_paddle.return_value = mock_ocr
        # PaddleOCR 返回格式：list[page] -> list[line] -> [bbox, (text, confidence)]
        mock_ocr.ocr.return_value = [
            [
                [[[10, 10], [50, 10], [50, 20], [10, 20]], ("发票代码：0440000000", 0.99)],
                [[[10, 30], [50, 30], [50, 40], [10, 40]], ("发票号码：12345678", 0.98)],
            ]
        ]
        with patch('core.ocr_engine.Image') as mock_image, \
             patch('core.ocr_engine.tempfile') as mock_tmp, \
             patch('core.ocr_engine.os.unlink'):
            mock_tmp.NamedTemporaryFile.return_value.__enter__.return_value.name = "tmp.png"
            engine = OcrEngine()
            result = engine._parse_ocr_result(mock_ocr.ocr.return_value)
            assert isinstance(result, list)
            assert "发票代码：0440000000" in result
            assert "发票号码：12345678" in result


def test_parse_ocr_result_filters_low_confidence():
    with patch('core.ocr_engine.PaddleOCR'):
        engine = OcrEngine()
        result_data = [
            [
                [[[0,0],[1,0],[1,1],[0,1]], ("高置信度文本", 0.95)],
                [[[0,0],[1,0],[1,1],[0,1]], ("低置信度文本", 0.50)],
            ]
        ]
        texts = engine._parse_ocr_result(result_data)
        assert "高置信度文本" in texts
        assert "低置信度文本" not in texts


def test_parse_ocr_result_handles_empty():
    with patch('core.ocr_engine.PaddleOCR'):
        engine = OcrEngine()
        assert engine._parse_ocr_result([]) == []
        assert engine._parse_ocr_result(None) == []


def test_extract_text_from_pdf_calls_convert(tmp_path):
    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 test")
    with patch('core.ocr_engine.PaddleOCR'), \
         patch('core.ocr_engine.convert_from_path') as mock_convert, \
         patch.object(OcrEngine, '_extract_from_pil_image', return_value=["发票代码：0440000000"]):
        mock_page = MagicMock()
        mock_convert.return_value = [mock_page]
        engine = OcrEngine()
        result = engine.extract_text_from_file(str(dummy_pdf))
        mock_convert.assert_called_once()
        assert result == ["发票代码：0440000000"]
```

- [ ] **步骤 2：运行测试，确认失败**

```bash
pytest tests/test_ocr_engine.py -v
```

期望：`ModuleNotFoundError: No module named 'core.ocr_engine'`

- [ ] **步骤 3：实现 OCR 引擎**

```python
# core/ocr_engine.py
import os
import tempfile
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from PIL import Image

_CONFIDENCE_THRESHOLD = 0.80
_PDF_DPI = 200


class OcrEngine:
    def __init__(self):
        self._ocr = PaddleOCR(use_angle_cls=True, lang='ch')

    def extract_text_from_file(self, file_path: str) -> list[str]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return self._extract_from_pdf(file_path)
        return self.extract_text_from_image(file_path)

    def _extract_from_pdf(self, pdf_path: str) -> list[str]:
        pages = convert_from_path(pdf_path, dpi=_PDF_DPI)
        texts = []
        for page in pages:
            page_texts = self._extract_from_pil_image(page)
            texts.extend(page_texts)
            combined = ' '.join(texts)
            if '发票代码' in combined and '发票号码' in combined:
                break
        return texts

    def extract_text_from_image(self, image_path: str) -> list[str]:
        img = Image.open(image_path)
        return self._extract_from_pil_image(img)

    def _extract_from_pil_image(self, img: Image.Image) -> list[str]:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
            img.save(tmp_path)
        try:
            result = self._ocr.ocr(tmp_path, cls=True)
            return self._parse_ocr_result(result)
        finally:
            os.unlink(tmp_path)

    def _parse_ocr_result(self, result) -> list[str]:
        if not result:
            return []
        texts = []
        for page in result:
            if not page:
                continue
            for line in page:
                text_info = line[1]
                if isinstance(text_info, (list, tuple)) and len(text_info) == 2:
                    text, confidence = text_info
                else:
                    text = str(text_info)
                    confidence = 1.0
                if confidence >= _CONFIDENCE_THRESHOLD:
                    texts.append(text)
        return texts
```

- [ ] **步骤 4：运行测试，确认通过**

```bash
pytest tests/test_ocr_engine.py -v
```

期望：5 个测试全部 PASS

- [ ] **步骤 5：提交**

```bash
git add core/ocr_engine.py tests/test_ocr_engine.py
git commit -m "feat: add OCR engine wrapping PaddleOCR with PDF and PNG support"
```

---

## Task 4：发票解析器

**文件：**
- 创建：`core/invoice_parser.py`
- 创建：`tests/test_invoice_parser.py`

- [ ] **步骤 1：编写失败测试**

```python
# tests/test_invoice_parser.py
from decimal import Decimal
from core.invoice_parser import InvoiceParser
from models.invoice import InvoiceStatus

# 模拟真实增值税专用发票 OCR 输出的文本列表
SAMPLE_TEXTS = [
    "增值税专用发票",
    "发票代码：044001900111",
    "发票号码：12345678",
    "开票日期：2024年03月15日",
    "购买方名称：深圳XX科技有限公司",
    "纳税人识别号：914403001234567890",
    "地址、电话：广东省深圳市南山区XX路100号",
    "销售方名称：广州YY贸易有限公司",
    "纳税人识别号：914401011234567891",
    "*信息技术服务*软件开发服务",
    "1",
    "次",
    "¥1000.00",
    "合计",
    "¥1000.00",
    "税率",
    "13%",
    "税额",
    "¥130.00",
    "价税合计（大写）壹仟壹佰叁拾元整",
    "（小写）¥1130.00",
    "开票人：张三",
]


def test_parse_invoice_code():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.invoice_code == "044001900111"


def test_parse_invoice_number():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.invoice_number == "12345678"


def test_parse_invoice_date():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.invoice_date == "2024-03-15"


def test_parse_buyer_name():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.buyer_name == "深圳XX科技有限公司"


def test_parse_buyer_tax_id():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.buyer_tax_id == "914403001234567890"


def test_parse_seller_name():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.seller_name == "广州YY贸易有限公司"


def test_parse_seller_tax_id():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.seller_tax_id == "914401011234567891"


def test_parse_total_amount():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.total_amount == Decimal("1130.00")


def test_parse_tax_rate():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.tax_rate == "13%"


def test_parse_tax_amount():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.tax_amount == Decimal("130.00")


def test_parse_invoice_type():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.invoice_type == "增值税专用发票"


def test_parse_issuer():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.issuer == "张三"


def test_parse_source_file():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "invoice_001.pdf")
    assert invoice.source_file == "invoice_001.pdf"


def test_parse_status_success():
    invoice = InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf")
    assert invoice.status == InvoiceStatus.SUCCESS


def test_parse_status_review_on_amount_mismatch():
    # 将总金额改为与不含税+税额不符
    texts = [t.replace("（小写）¥1130.00", "（小写）¥1200.00") for t in SAMPLE_TEXTS]
    invoice = InvoiceParser().parse(texts, "test.pdf")
    assert invoice.status == InvoiceStatus.REVIEW


def test_parse_empty_texts_returns_failed():
    invoice = InvoiceParser().parse([], "empty.pdf")
    assert invoice.status == InvoiceStatus.FAILED
    assert invoice.error_message != ""


def test_parse_missing_code_returns_review():
    texts = [t for t in SAMPLE_TEXTS if "发票代码" not in t]
    invoice = InvoiceParser().parse(texts, "test.pdf")
    assert invoice.status == InvoiceStatus.REVIEW
```

- [ ] **步骤 2：运行测试，确认失败**

```bash
pytest tests/test_invoice_parser.py -v
```

期望：`ModuleNotFoundError: No module named 'core.invoice_parser'`

- [ ] **步骤 3：实现发票解析器**

```python
# core/invoice_parser.py
import re
from decimal import Decimal, InvalidOperation
from models.invoice import Invoice, InvoiceStatus

_INVOICE_TYPES = [
    "增值税专用发票", "增值税普通发票",
    "增值税电子专用发票", "增值税电子普通发票",
]

_RE_CODE    = re.compile(r'发票代码[：:]\s*(\d{10,12})')
_RE_NUMBER  = re.compile(r'发票号码[：:]\s*(\d{7,8})')
_RE_DATE    = re.compile(r'开票日期[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日')
_RE_TAX_ID  = re.compile(r'纳税人识别号[：:]\s*([A-Za-z0-9]{15,20})')
_RE_TAX_RATE= re.compile(r'税率\s*[：:]?\s*(\d+%|免税|零税率)')
_RE_TOTAL_LOWER = re.compile(r'[（(]小写[）)]\s*[¥￥]\s*([\d,]+\.?\d*)')
_RE_AMOUNT  = re.compile(r'[¥￥]\s*([\d,]+\.?\d*)')
_RE_ISSUER  = re.compile(r'开票人[：:]\s*(.+)')

_REQUIRED_FIELDS = ['invoice_code', 'invoice_number', 'invoice_date', 'buyer_name', 'seller_name']


class InvoiceParser:
    def parse(self, texts: list[str], source_file: str) -> Invoice:
        if not texts:
            return Invoice(
                source_file=source_file,
                status=InvoiceStatus.FAILED,
                error_message="OCR 未返回任何文本",
            )

        full_text = '\n'.join(texts)
        invoice = Invoice(source_file=source_file)

        invoice.invoice_type  = self._find_invoice_type(texts)
        invoice.invoice_code  = self._search(full_text, _RE_CODE, 1)
        invoice.invoice_number = self._search(full_text, _RE_NUMBER, 1)
        invoice.invoice_date  = self._extract_date(full_text)
        invoice.buyer_name, invoice.buyer_tax_id = self._extract_party(full_text, "购买方", tax_index=0)
        invoice.seller_name, invoice.seller_tax_id = self._extract_party(full_text, "销售方", tax_index=1)
        invoice.tax_rate      = self._search(full_text, _RE_TAX_RATE, 1)
        invoice.total_amount  = self._extract_total(full_text)
        invoice.tax_amount, invoice.subtotal = self._extract_sub_amounts(full_text)
        issuer_raw            = self._search(full_text, _RE_ISSUER, 1)
        invoice.issuer        = issuer_raw.strip()

        invoice.status = self._determine_status(invoice)
        return invoice

    # ── private helpers ──────────────────────────────────────────────────────

    def _find_invoice_type(self, texts: list[str]) -> str:
        for text in texts:
            for t in _INVOICE_TYPES:
                if t in text:
                    return t
        return ""

    def _search(self, text: str, pattern: re.Pattern, group: int) -> str:
        m = pattern.search(text)
        return m.group(group) if m else ""

    def _extract_date(self, text: str) -> str:
        m = _RE_DATE.search(text)
        if not m:
            return ""
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"

    def _extract_party(self, text: str, party: str, tax_index: int) -> tuple[str, str]:
        name_pat = re.compile(rf'{party}名称[：:]\s*(.+)')
        m = name_pat.search(text)
        name = m.group(1).strip() if m else ""
        tax_ids = _RE_TAX_ID.findall(text)
        tax_id = tax_ids[tax_index] if len(tax_ids) > tax_index else ""
        return name, tax_id

    def _extract_total(self, text: str) -> Decimal:
        m = _RE_TOTAL_LOWER.search(text)
        if m:
            return self._to_decimal(m.group(1))
        amounts = _RE_AMOUNT.findall(text)
        return self._to_decimal(amounts[-1]) if amounts else Decimal("0")

    def _extract_sub_amounts(self, text: str) -> tuple[Decimal, Decimal]:
        amounts = _RE_AMOUNT.findall(text)
        if len(amounts) >= 2:
            return self._to_decimal(amounts[1]), self._to_decimal(amounts[0])
        return Decimal("0"), Decimal("0")

    def _to_decimal(self, value: str) -> Decimal:
        try:
            return Decimal(value.replace(',', ''))
        except InvalidOperation:
            return Decimal("0")

    def _determine_status(self, invoice: Invoice) -> str:
        missing = [f for f in _REQUIRED_FIELDS if not getattr(invoice, f)]
        if missing:
            return InvoiceStatus.REVIEW

        if invoice.subtotal and invoice.tax_amount:
            expected = invoice.subtotal + invoice.tax_amount
            if abs(expected - invoice.total_amount) > Decimal("0.01"):
                return InvoiceStatus.REVIEW

        return InvoiceStatus.SUCCESS
```

- [ ] **步骤 4：运行测试，确认通过**

```bash
pytest tests/test_invoice_parser.py -v
```

期望：17 个测试全部 PASS

- [ ] **步骤 5：提交**

```bash
git add core/invoice_parser.py tests/test_invoice_parser.py
git commit -m "feat: add invoice parser with regex field extraction and amount validation"
```

---

## Task 5：Excel 导出器

**文件：**
- 创建：`core/exporter.py`
- 创建：`tests/test_exporter.py`

- [ ] **步骤 1：编写失败测试**

```python
# tests/test_exporter.py
import os
import tempfile
import openpyxl
from decimal import Decimal
from core.exporter import Exporter, ExportMode
from models.invoice import Invoice, InvoiceItem, InvoiceStatus


def _make_invoice(code="044001900111", number="12345678") -> Invoice:
    return Invoice(
        source_file="test.pdf",
        invoice_code=code,
        invoice_number=number,
        invoice_date="2024-03-15",
        buyer_name="深圳XX科技有限公司",
        buyer_tax_id="914403001234567890",
        seller_name="广州YY贸易有限公司",
        seller_tax_id="914401011234567891",
        items=[InvoiceItem(name="软件开发服务", quantity="1",
                           unit_price=Decimal("1000.00"), amount=Decimal("1000.00"))],
        subtotal=Decimal("1000.00"),
        tax_rate="13%",
        tax_amount=Decimal("130.00"),
        total_amount=Decimal("1130.00"),
        issuer="张三",
        invoice_type="增值税专用发票",
        status=InvoiceStatus.SUCCESS,
    )


def test_export_summary_creates_excel():
    exporter = Exporter()
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        exporter.export([_make_invoice()], path, ExportMode.SUMMARY)
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        assert ws.max_row == 2  # 表头 + 1 行数据
    finally:
        os.unlink(path)


def test_export_summary_has_required_headers():
    exporter = Exporter()
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        exporter.export([_make_invoice()], path, ExportMode.SUMMARY)
        wb = openpyxl.load_workbook(path)
        headers = [ws.cell(1, col).value for col in range(1, wb.active.max_column + 1)
                   for ws in [wb.active]]
        for required in ["发票代码", "发票号码", "价税合计", "购买方名称", "销售方名称"]:
            assert required in headers
    finally:
        os.unlink(path)


def test_export_summary_data_row_values():
    exporter = Exporter()
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        exporter.export([_make_invoice("044001900111", "12345678")], path, ExportMode.SUMMARY)
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        row2 = [ws.cell(2, col).value for col in range(1, ws.max_column + 1)]
        assert "044001900111" in row2
        assert "12345678" in row2
    finally:
        os.unlink(path)


def test_export_detail_expands_items():
    inv = _make_invoice()
    inv.items = [
        InvoiceItem(name="服务A", quantity="1", unit_price=Decimal("500"), amount=Decimal("500")),
        InvoiceItem(name="服务B", quantity="2", unit_price=Decimal("250"), amount=Decimal("500")),
    ]
    exporter = Exporter()
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        exporter.export([inv], path, ExportMode.DETAIL)
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        assert ws.max_row == 3  # 表头 + 2 条明细行
    finally:
        os.unlink(path)


def test_export_multiple_invoices_summary():
    invoices = [_make_invoice("111", "001"), _make_invoice("222", "002")]
    exporter = Exporter()
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        exporter.export(invoices, path, ExportMode.SUMMARY)
        wb = openpyxl.load_workbook(path)
        assert wb.active.max_row == 3  # 表头 + 2 行
    finally:
        os.unlink(path)


def test_export_invoice_without_items_detail():
    inv = _make_invoice()
    inv.items = []
    exporter = Exporter()
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        exporter.export([inv], path, ExportMode.DETAIL)
        wb = openpyxl.load_workbook(path)
        assert wb.active.max_row == 2  # 表头 + 1 空明细行
    finally:
        os.unlink(path)
```

- [ ] **步骤 2：运行测试，确认失败**

```bash
pytest tests/test_exporter.py -v
```

期望：`ModuleNotFoundError: No module named 'core.exporter'`

- [ ] **步骤 3：实现导出器**

```python
# core/exporter.py
from enum import Enum
from decimal import Decimal
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from models.invoice import Invoice, InvoiceItem


class ExportMode(Enum):
    SUMMARY = "summary"
    DETAIL = "detail"


_SUMMARY_HEADERS = [
    "来源文件", "发票类型", "发票代码", "发票号码", "开票日期",
    "购买方名称", "购买方税号", "销售方名称", "销售方税号",
    "不含税金额", "税率", "税额", "价税合计", "开票人", "状态",
]

_DETAIL_HEADERS = [
    "来源文件", "发票代码", "发票号码", "开票日期",
    "购买方名称", "销售方名称",
    "货物/服务名称", "数量", "单价", "金额",
    "税率", "税额", "价税合计",
]


class Exporter:
    def export(self, invoices: list[Invoice], output_path: str, mode: ExportMode) -> None:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "汇总" if mode == ExportMode.SUMMARY else "明细"

        if mode == ExportMode.SUMMARY:
            self._write_summary(ws, invoices)
        else:
            self._write_detail(ws, invoices)

        wb.save(output_path)

    def _write_summary(self, ws, invoices: list[Invoice]) -> None:
        self._write_header(ws, _SUMMARY_HEADERS)
        for inv in invoices:
            ws.append([
                inv.source_file, inv.invoice_type,
                inv.invoice_code, inv.invoice_number, inv.invoice_date,
                inv.buyer_name, inv.buyer_tax_id,
                inv.seller_name, inv.seller_tax_id,
                str(inv.subtotal), inv.tax_rate, str(inv.tax_amount),
                str(inv.total_amount), inv.issuer, inv.status,
            ])

    def _write_detail(self, ws, invoices: list[Invoice]) -> None:
        self._write_header(ws, _DETAIL_HEADERS)
        for inv in invoices:
            items = inv.items if inv.items else [None]
            for item in items:
                ws.append([
                    inv.source_file, inv.invoice_code, inv.invoice_number,
                    inv.invoice_date, inv.buyer_name, inv.seller_name,
                    item.name if item else "",
                    item.quantity if item else "",
                    str(item.unit_price) if item else "",
                    str(item.amount) if item else "",
                    inv.tax_rate, str(inv.tax_amount), str(inv.total_amount),
                ])

    def _write_header(self, ws, headers: list[str]) -> None:
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="DDEEFF", end_color="DDEEFF", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
```

- [ ] **步骤 4：运行测试，确认通过**

```bash
pytest tests/test_exporter.py -v
```

期望：6 个测试全部 PASS

- [ ] **步骤 5：提交**

```bash
git add core/exporter.py tests/test_exporter.py
git commit -m "feat: add Excel exporter with summary and detail modes"
```

---

## Task 6：进度弹窗

**文件：**
- 创建：`ui/progress_dialog.py`

- [ ] **步骤 1：实现进度弹窗**

```python
# ui/progress_dialog.py
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
```

- [ ] **步骤 2：提交**

```bash
git add ui/progress_dialog.py
git commit -m "feat: add batch processing progress dialog"
```

---

## Task 7：预览与编辑面板

**文件：**
- 创建：`ui/preview_panel.py`

- [ ] **步骤 1：实现预览面板**

```python
# ui/preview_panel.py
from decimal import Decimal, InvalidOperation
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QLabel, QPushButton, QScrollArea,
)
from PyQt6.QtCore import pyqtSignal
from models.invoice import Invoice


_FIELD_LABELS = [
    ("invoice_code",   "发票代码"),
    ("invoice_number", "发票号码"),
    ("invoice_date",   "开票日期"),
    ("invoice_type",   "发票类型"),
    ("buyer_name",     "购买方名称"),
    ("buyer_tax_id",   "购买方税号"),
    ("seller_name",    "销售方名称"),
    ("seller_tax_id",  "销售方税号"),
    ("subtotal",       "不含税金额"),
    ("tax_rate",       "税率"),
    ("tax_amount",     "税额"),
    ("total_amount",   "价税合计"),
    ("issuer",         "开票人"),
]

_DECIMAL_FIELDS = {"subtotal", "tax_amount", "total_amount"}


class PreviewPanel(QWidget):
    invoice_changed = pyqtSignal(Invoice)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._invoice: Invoice | None = None
        self._fields: dict[str, QLineEdit] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("发票详情", self)
        layout.addWidget(title)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        form = QFormLayout(form_widget)
        scroll.setWidget(form_widget)
        layout.addWidget(scroll)

        for field_name, label_text in _FIELD_LABELS:
            edit = QLineEdit(self)
            edit.setPlaceholderText("(未识别)")
            self._fields[field_name] = edit
            form.addRow(label_text + "：", edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("保存修改", self)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def show_invoice(self, invoice: Invoice) -> None:
        self._invoice = invoice
        for field_name, edit in self._fields.items():
            value = getattr(invoice, field_name, "")
            edit.setText(str(value) if value else "")

    def clear(self) -> None:
        self._invoice = None
        for edit in self._fields.values():
            edit.clear()

    def _on_save(self) -> None:
        if not self._invoice:
            return
        for field_name, edit in self._fields.items():
            text = edit.text().strip()
            if field_name in _DECIMAL_FIELDS:
                try:
                    setattr(self._invoice, field_name, Decimal(text) if text else Decimal("0"))
                except InvalidOperation:
                    pass
            else:
                setattr(self._invoice, field_name, text)
        self.invoice_changed.emit(self._invoice)
```

- [ ] **步骤 2：提交**

```bash
git add ui/preview_panel.py
git commit -m "feat: add invoice preview and field editing panel"
```

---

## Task 8：主窗口

**文件：**
- 创建：`ui/main_window.py`

- [ ] **步骤 1：实现主窗口**

```python
# ui/main_window.py
import os
from PyQt6.QtWidgets import (
    QMainWindow, QListWidget, QListWidgetItem, QToolBar,
    QStatusBar, QFileDialog, QMessageBox, QSplitter, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent
from models.invoice import Invoice, InvoiceStatus
from core.ocr_engine import OcrEngine
from core.invoice_parser import InvoiceParser
from core.exporter import Exporter, ExportMode
from ui.preview_panel import PreviewPanel
from ui.progress_dialog import ProgressDialog

_STATUS_ICONS = {
    InvoiceStatus.PENDING:    "○",
    InvoiceStatus.PROCESSING: "…",
    InvoiceStatus.SUCCESS:    "✓",
    InvoiceStatus.REVIEW:     "⚠",
    InvoiceStatus.FAILED:     "✗",
}


def _find_duplicates(invoices: list[Invoice]) -> list[tuple[str, str]]:
    seen: dict[tuple[str, str], bool] = {}
    duplicates: list[tuple[str, str]] = []
    for inv in invoices:
        if not inv.invoice_code or not inv.invoice_number:
            continue
        key = (inv.invoice_code, inv.invoice_number)
        if key in seen:
            if key not in duplicates:
                duplicates.append(key)
        else:
            seen[key] = True
    return duplicates


class _OcrWorker(QObject):
    progress = pyqtSignal(int, str)
    invoice_done = pyqtSignal(int, Invoice)
    finished = pyqtSignal()

    def __init__(self, file_paths: list[str]):
        super().__init__()
        self._file_paths = file_paths
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        engine = OcrEngine()
        parser = InvoiceParser()
        for i, path in enumerate(self._file_paths):
            if self._cancelled:
                break
            self.progress.emit(i + 1, os.path.basename(path))
            try:
                texts = engine.extract_text_from_file(path)
                invoice = parser.parse(texts, source_file=os.path.basename(path))
            except Exception as exc:
                invoice = Invoice(
                    source_file=os.path.basename(path),
                    status=InvoiceStatus.FAILED,
                    error_message=str(exc),
                )
            self.invoice_done.emit(i, invoice)
        self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("发票扫描识别系统")
        self.setMinimumSize(1000, 600)
        self.setAcceptDrops(True)
        self._file_paths: list[str] = []
        self._invoices: list[Invoice] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        toolbar = QToolBar(self)
        self.addToolBar(toolbar)
        for label, slot in [("选择文件", self._on_add_files),
                             ("选择文件夹", self._on_add_folder),
                             ("清空列表", self._on_clear)]:
            act = QAction(label, self)
            act.triggered.connect(slot)
            toolbar.addAction(act)
        toolbar.addSeparator()
        start_act = QAction("开始识别", self)
        start_act.triggered.connect(self._on_start_ocr)
        toolbar.addAction(start_act)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.setCentralWidget(splitter)

        self._file_list = QListWidget(self)
        self._file_list.currentRowChanged.connect(self._on_file_selected)
        splitter.addWidget(self._file_list)

        self._preview = PreviewPanel(self)
        self._preview.invoice_changed.connect(self._on_invoice_changed)
        splitter.addWidget(self._preview)
        splitter.setSizes([350, 650])

        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        self._stats_label = QLabel("文件数: 0", self)
        status_bar.addWidget(self._stats_label)
        export_btn = QPushButton("导出 Excel", self)
        export_btn.clicked.connect(self._on_export)
        status_bar.addPermanentWidget(export_btn)

    # ── drag-drop ─────────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                paths += [os.path.join(path, f) for f in os.listdir(path)
                          if f.lower().endswith(('.pdf', '.png'))]
            elif path.lower().endswith(('.pdf', '.png')):
                paths.append(path)
        self._add_files(paths)

    # ── toolbar actions ───────────────────────────────────────────────────────

    def _on_add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "选择发票文件", "", "发票文件 (*.pdf *.png)")
        self._add_files(paths)

    def _on_add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            paths = [os.path.join(folder, f) for f in os.listdir(folder)
                     if f.lower().endswith(('.pdf', '.png'))]
            self._add_files(paths)

    def _on_clear(self) -> None:
        self._file_paths.clear()
        self._invoices.clear()
        self._file_list.clear()
        self._preview.clear()
        self._update_stats()

    def _add_files(self, paths: list[str]) -> None:
        existing = set(self._file_paths)
        for path in paths:
            if path not in existing:
                self._file_paths.append(path)
                self._invoices.append(Invoice(source_file=os.path.basename(path)))
                icon = _STATUS_ICONS[InvoiceStatus.PENDING]
                self._file_list.addItem(QListWidgetItem(f"{icon} {os.path.basename(path)}"))
        self._update_stats()

    # ── file list selection ───────────────────────────────────────────────────

    def _on_file_selected(self, row: int) -> None:
        if 0 <= row < len(self._invoices):
            self._preview.show_invoice(self._invoices[row])

    def _on_invoice_changed(self, invoice: Invoice) -> None:
        row = self._file_list.currentRow()
        if 0 <= row < len(self._invoices):
            self._invoices[row] = invoice
            icon = _STATUS_ICONS.get(invoice.status, "○")
            self._file_list.item(row).setText(f"{icon} {invoice.source_file}")

    # ── OCR processing ────────────────────────────────────────────────────────

    def _on_start_ocr(self) -> None:
        if not self._file_paths:
            QMessageBox.information(self, "提示", "请先添加发票文件")
            return
        self._progress_dlg = ProgressDialog(len(self._file_paths), self)
        self._worker = _OcrWorker(self._file_paths)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_ocr_progress)
        self._worker.invoice_done.connect(self._on_invoice_done)
        self._worker.finished.connect(self._on_ocr_finished)
        self._progress_dlg.rejected.connect(self._worker.cancel)
        self._thread.start()
        self._progress_dlg.exec()

    def _on_ocr_progress(self, current: int, filename: str) -> None:
        self._progress_dlg.update_progress(current, filename)
        item = self._file_list.item(current - 1)
        if item:
            item.setText(f"{_STATUS_ICONS[InvoiceStatus.PROCESSING]} {filename}")

    def _on_invoice_done(self, row: int, invoice: Invoice) -> None:
        self._invoices[row] = invoice
        item = self._file_list.item(row)
        if item:
            icon = _STATUS_ICONS.get(invoice.status, "○")
            item.setText(f"{icon} {invoice.source_file}")
        self._update_stats()

    def _on_ocr_finished(self) -> None:
        self._thread.quit()
        self._progress_dlg.close()
        self._update_stats()
        duplicates = _find_duplicates(self._invoices)
        if duplicates:
            msg = "检测到重复发票：\n" + "\n".join(
                f"发票代码 {code}  号码 {num}" for code, num in duplicates
            )
            QMessageBox.warning(self, "重复发票提示", msg)

    # ── export ────────────────────────────────────────────────────────────────

    def _on_export(self) -> None:
        if not self._invoices:
            QMessageBox.information(self, "提示", "没有可导出的数据")
            return
        reply = QMessageBox.question(
            self, "导出模式",
            "点击"是"→汇总模式（每张发票一行）\n点击"否"→明细模式（每条明细一行）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        mode = ExportMode.SUMMARY if reply == QMessageBox.StandardButton.Yes else ExportMode.DETAIL
        path, _ = QFileDialog.getSaveFileName(self, "保存 Excel", "", "Excel 文件 (*.xlsx)")
        if not path:
            return
        try:
            Exporter().export(self._invoices, path, mode)
            QMessageBox.information(self, "导出成功", f"已保存到：{path}")
        except PermissionError:
            QMessageBox.critical(self, "导出失败", f"文件被占用，请关闭 {path} 后重试")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    # ── stats ─────────────────────────────────────────────────────────────────

    def _update_stats(self) -> None:
        total    = len(self._invoices)
        success  = sum(1 for i in self._invoices if i.status == InvoiceStatus.SUCCESS)
        review   = sum(1 for i in self._invoices if i.status == InvoiceStatus.REVIEW)
        failed   = sum(1 for i in self._invoices if i.status == InvoiceStatus.FAILED)
        self._stats_label.setText(
            f"文件数: {total}   已完成: {success}   需复核: {review}   失败: {failed}"
        )
```

- [ ] **步骤 2：提交**

```bash
git add ui/main_window.py
git commit -m "feat: add main window with file list, toolbar, drag-drop, and OCR worker"
```

---

## Task 9：重复发票检测测试

**文件：**
- 创建：`tests/test_main_window.py`

- [ ] **步骤 1：编写失败测试**

```python
# tests/test_main_window.py
from models.invoice import Invoice
from ui.main_window import _find_duplicates


def test_find_duplicates_same_code_and_number():
    invoices = [
        Invoice(invoice_code="044001900111", invoice_number="12345678", source_file="a.pdf"),
        Invoice(invoice_code="044001900111", invoice_number="12345678", source_file="b.pdf"),
    ]
    result = _find_duplicates(invoices)
    assert result == [("044001900111", "12345678")]


def test_find_duplicates_different_numbers_no_dup():
    invoices = [
        Invoice(invoice_code="044001900111", invoice_number="12345678", source_file="a.pdf"),
        Invoice(invoice_code="044001900111", invoice_number="99999999", source_file="b.pdf"),
    ]
    assert _find_duplicates(invoices) == []


def test_find_duplicates_empty_code_ignored():
    invoices = [
        Invoice(invoice_code="", invoice_number="12345678", source_file="a.pdf"),
        Invoice(invoice_code="", invoice_number="12345678", source_file="b.pdf"),
    ]
    assert _find_duplicates(invoices) == []


def test_find_duplicates_reports_each_key_once():
    invoices = [
        Invoice(invoice_code="111", invoice_number="001", source_file="a.pdf"),
        Invoice(invoice_code="111", invoice_number="001", source_file="b.pdf"),
        Invoice(invoice_code="111", invoice_number="001", source_file="c.pdf"),
    ]
    result = _find_duplicates(invoices)
    assert len(result) == 1
```

- [ ] **步骤 2：运行测试，确认通过**

```bash
pytest tests/test_main_window.py -v
```

期望：4 个测试全部 PASS（`_find_duplicates` 已在 Task 8 中实现）

- [ ] **步骤 3：提交**

```bash
git add tests/test_main_window.py
git commit -m "test: add duplicate invoice detection unit tests"
```

---

## Task 10：应用入口

**文件：**
- 创建：`main.py`

- [ ] **步骤 1：实现应用入口**

```python
# main.py
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("发票扫描识别系统")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：启动应用，验证界面正常**

```bash
python main.py
```

手动验证：
- [ ] 主窗口出现，标题正确
- [ ] 工具栏显示"选择文件"、"选择文件夹"、"清空列表"、"开始识别"
- [ ] 状态栏显示"文件数: 0"和"导出 Excel"按钮

- [ ] **步骤 3：提交**

```bash
git add main.py
git commit -m "feat: add application entry point"
```

---

## Task 11：完整测试套件验收

- [ ] **步骤 1：运行全部自动化测试**

```bash
pytest tests/ -v --tb=short
```

期望：全部通过（tests/ 下所有 test_*.py）

- [ ] **步骤 2：检查测试覆盖率**

```bash
pytest tests/ --cov=core --cov=models --cov-report=term-missing
```

期望：`core/` 和 `models/` 覆盖率 ≥ 80%

- [ ] **步骤 3：端到端手动验收**

准备 1-2 张真实增值税发票（PDF 或 PNG），执行完整流程：

```bash
python main.py
```

操作步骤：
- [ ] 将发票文件拖入主窗口 → 文件出现在列表，状态图标为 ○
- [ ] 点击"开始识别" → 进度弹窗出现，处理完成后图标变为 ✓/⚠/✗
- [ ] 点击列表中的发票 → 右侧面板显示解析出的字段
- [ ] 修改某字段后点击"保存修改" → 确认字段已更新
- [ ] 点击"导出 Excel" → 选择汇总模式 → 保存文件 → 用 Excel 打开确认内容

- [ ] **步骤 4：最终提交**

```bash
git add .
git commit -m "test: complete test suite passing with ≥80% coverage"
```

---

## 验收标准清单

- [ ] 支持 PDF 和 PNG 格式批量导入（含拖拽）
- [ ] 识别结果分状态显示（✓ 成功 / ⚠ 需复核 / ✗ 失败 / … 处理中）
- [ ] 识别失败或需复核的文件有明确提示
- [ ] 右侧面板可手动编辑修正所有字段
- [ ] 导出 Excel 包含所有定义字段，支持汇总和明细两种模式
- [ ] 批量处理不阻塞 UI，进度实时可见
- [ ] 重复发票（相同代码+号码）有去重弹窗提示
- [ ] 金额不符（合计 ≠ 不含税 + 税额）时自动标记需复核
- [ ] 测试覆盖率 ≥ 80%（core/ + models/）
