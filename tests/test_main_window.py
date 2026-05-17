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
