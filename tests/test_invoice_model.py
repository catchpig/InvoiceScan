from decimal import Decimal
from models.invoice import Invoice, InvoiceStatus


def test_invoice_creation_defaults():
    inv = Invoice(source_file="test.pdf")
    assert inv.source_file == "test.pdf"
    assert inv.status == InvoiceStatus.PENDING
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
