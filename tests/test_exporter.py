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
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        Exporter().export([_make_invoice()], path, ExportMode.SUMMARY)
        wb = openpyxl.load_workbook(path)
        assert wb.active.max_row == 2  # 表头 + 1 行数据
    finally:
        os.unlink(path)


def test_export_summary_has_required_headers():
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        Exporter().export([_make_invoice()], path, ExportMode.SUMMARY)
        ws = openpyxl.load_workbook(path).active
        headers = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]
        for required in ["发票代码", "发票号码", "价税合计", "购买方名称", "销售方名称"]:
            assert required in headers
    finally:
        os.unlink(path)


def test_export_summary_data_row_values():
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        Exporter().export([_make_invoice("044001900111", "12345678")], path, ExportMode.SUMMARY)
        ws = openpyxl.load_workbook(path).active
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
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        Exporter().export([inv], path, ExportMode.DETAIL)
        ws = openpyxl.load_workbook(path).active
        assert ws.max_row == 3  # 表头 + 2 条明细行
    finally:
        os.unlink(path)


def test_export_multiple_invoices_summary():
    invoices = [_make_invoice("111", "001"), _make_invoice("222", "002")]
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        Exporter().export(invoices, path, ExportMode.SUMMARY)
        assert openpyxl.load_workbook(path).active.max_row == 3
    finally:
        os.unlink(path)


def test_export_invoice_without_items_detail():
    inv = _make_invoice()
    inv.items = []
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    try:
        Exporter().export([inv], path, ExportMode.DETAIL)
        assert openpyxl.load_workbook(path).active.max_row == 2
    finally:
        os.unlink(path)
