import re
from decimal import Decimal, InvalidOperation
from models.invoice import Invoice, InvoiceStatus

_INVOICE_TYPES = [
    "增值税专用发票", "增值税普通发票",
    "增值税电子专用发票", "增值税电子普通发票",
]

_RE_CODE     = re.compile(r'发票代码[：:]\s*(\d{10,12})')
_RE_NUMBER   = re.compile(r'发票号码[：:]\s*(\d{7,8})')
_RE_DATE     = re.compile(r'开票日期[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日')
_RE_TAX_ID   = re.compile(r'纳税人识别号[：:]\s*([A-Za-z0-9]{15,20})')
_RE_TAX_RATE   = re.compile(r'税率\s*[：:]?\s*(\d+%|免税|零税率)')
_RE_TOTAL_LOWER = re.compile(r'[（(]小写[）)]\s*[¥￥]\s*([\d,]+\.?\d*)')
_RE_AMOUNT     = re.compile(r'[¥￥]\s*([\d,]+\.?\d*)')
_RE_TAX_AMOUNT = re.compile(r'税额\s*\n\s*[¥￥]\s*([\d,]+\.?\d*)')
_RE_SUBTOTAL   = re.compile(r'合计\s*\n\s*[¥￥]\s*([\d,]+\.?\d*)')
_RE_ISSUER     = re.compile(r'开票人[：:]\s*(.+)')

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

        invoice.invoice_type   = self._find_invoice_type(texts)
        invoice.invoice_code   = self._search(full_text, _RE_CODE, 1)
        invoice.invoice_number = self._search(full_text, _RE_NUMBER, 1)
        invoice.invoice_date   = self._extract_date(full_text)
        invoice.buyer_name, invoice.buyer_tax_id   = self._extract_party(full_text, "购买方", 0)
        invoice.seller_name, invoice.seller_tax_id = self._extract_party(full_text, "销售方", 1)
        invoice.tax_rate       = self._search(full_text, _RE_TAX_RATE, 1)
        invoice.total_amount   = self._extract_total(full_text)
        invoice.tax_amount, invoice.subtotal = self._extract_sub_amounts(full_text)
        issuer_raw             = self._search(full_text, _RE_ISSUER, 1)
        invoice.issuer         = issuer_raw.strip()

        invoice.status = self._determine_status(invoice)
        return invoice

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
        # 优先按语义标签提取（税额在"税额"标签之后）
        tax_m = _RE_TAX_AMOUNT.search(text)
        if tax_m:
            tax = self._to_decimal(tax_m.group(1))
            sub_m = _RE_SUBTOTAL.search(text)
            subtotal = self._to_decimal(sub_m.group(1)) if sub_m else Decimal("0")
            return tax, subtotal

        # 回退：取所有金额列表，排除 total，取最后两个
        amounts = _RE_AMOUNT.findall(text)
        total_m = _RE_TOTAL_LOWER.search(text)
        total_str = total_m.group(1) if total_m else ""
        filtered = [a for a in amounts if a != total_str]
        if len(filtered) >= 2:
            return self._to_decimal(filtered[-1]), self._to_decimal(filtered[-2])
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
