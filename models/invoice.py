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
