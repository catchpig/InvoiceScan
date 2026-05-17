# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from core.ocr_engine import OcrEngine
from core.invoice_parser import InvoiceParser

img_path = os.path.join('images', '发票.png')  # images/发票.png
engine = OcrEngine()
texts = engine.extract_text_from_file(img_path)
parser = InvoiceParser()
invoice = parser.parse(texts, img_path)

lines = [
    '=== Invoice Final Result ===',
    'Type:       ' + invoice.invoice_type,
    'Number:     ' + invoice.invoice_number,
    'Date:       ' + invoice.invoice_date,
    'Buyer:      ' + invoice.buyer_name,
    'BuyerTaxID: ' + (invoice.buyer_tax_id or '(none)'),
    'Seller:     ' + invoice.seller_name,
    'SellerTaxID:' + (invoice.seller_tax_id or '(none)'),
    'Total:      ' + str(invoice.total_amount),
    'Tax:        ' + str(invoice.tax_amount),
    'Subtotal:   ' + str(invoice.subtotal),
    'Issuer:     ' + invoice.issuer,
    'Status:     ' + invoice.status,
]
for l in lines:
    print(l)
