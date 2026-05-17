from models.invoice import Invoice, InvoiceStatus
from ui.main_window import _find_duplicates, _STATUS_STYLES


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


def test_status_styles_covers_all_statuses():
    for status in [
        InvoiceStatus.PENDING, InvoiceStatus.PROCESSING,
        InvoiceStatus.SUCCESS, InvoiceStatus.REVIEW, InvoiceStatus.FAILED,
    ]:
        assert status in _STATUS_STYLES, f"缺少状态: {status}"
        assert _STATUS_STYLES[status].get("text"), f"{status} 的文字为空"


def test_status_styles_text_values():
    assert _STATUS_STYLES[InvoiceStatus.PENDING]["text"]    == "等待"
    assert _STATUS_STYLES[InvoiceStatus.PROCESSING]["text"] == "识别中"
    assert _STATUS_STYLES[InvoiceStatus.SUCCESS]["text"]    == "完成"
    assert _STATUS_STYLES[InvoiceStatus.REVIEW]["text"]     == "需复核"
    assert _STATUS_STYLES[InvoiceStatus.FAILED]["text"]     == "失败"
