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
    export_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._invoice: Invoice | None = None
        self._fields: dict[str, QLineEdit] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("发票详情", self))

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
        export_btn = QPushButton("导出 Excel", self)
        export_btn.clicked.connect(self.export_requested)
        btn_row.addWidget(export_btn)
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
