from decimal import Decimal, InvalidOperation
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QLabel, QPushButton, QScrollArea, QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt
from models.invoice import Invoice, InvoiceStatus
from ui.theme import COLORS

_FIELD_LABELS = [
    ("invoice_code",   "发票代码"),
    ("invoice_number", "发票号码"),
    ("invoice_date",   "开票日期"),
    ("invoice_type",   "发票类型"),
]

_BUYER_FIELDS = [
    ("buyer_name",     "购买方名称"),
    ("buyer_tax_id",   "购买方税号"),
]

_SELLER_FIELDS = [
    ("seller_name",    "销售方名称"),
    ("seller_tax_id",  "销售方税号"),
]

_AMOUNT_FIELDS = [
    ("subtotal",       "不含税金额"),
    ("tax_rate",       "税率"),
    ("tax_amount",     "税额"),
    ("total_amount",   "价税合计"),
]

_DECIMAL_FIELDS = {"subtotal", "tax_amount", "total_amount"}


class _SectionHeader(QFrame):
    """A subtle section divider with a label."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)

        label = QLabel(title, self)
        label.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {COLORS['text_secondary']}; "
            f"letter-spacing: 1px; text-transform: uppercase;"
        )

        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {COLORS['border']};")
        line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(label)
        layout.addWidget(line)


class PreviewPanel(QWidget):
    invoice_changed = pyqtSignal(Invoice)
    export_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._invoice: Invoice | None = None
        self._fields: dict[str, QLineEdit] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── panel header ──
        header = QFrame(self)
        header.setFixedHeight(44)
        header.setStyleSheet(
            f"background: {COLORS['bg_surface']}; border-bottom: 1px solid {COLORS['border']};"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("📝 发票详情", self)
        title.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {COLORS['text_primary']};"
        )

        self._status_badge = QLabel("", self)
        self._status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_badge.setFixedHeight(24)
        self._status_badge.setVisible(False)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self._status_badge)
        outer.addWidget(header)

        # ── scrollable form ──
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")

        form_container = QWidget()
        form_container.setStyleSheet(f"background: {COLORS['bg_surface']};")
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(24, 16, 24, 16)
        form_layout.setSpacing(6)

        # Basic info section
        form_layout.addWidget(_SectionHeader("基本信息"))
        basic_form = QFormLayout()
        basic_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        basic_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        basic_form.setHorizontalSpacing(16)
        basic_form.setVerticalSpacing(8)
        for field_name, label_text in _FIELD_LABELS:
            edit = self._make_edit()
            self._fields[field_name] = edit
            basic_form.addRow(self._make_label(label_text), edit)
        form_layout.addLayout(basic_form)

        # Buyer section
        form_layout.addWidget(_SectionHeader("购买方"))
        buyer_form = QFormLayout()
        buyer_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        buyer_form.setHorizontalSpacing(16)
        buyer_form.setVerticalSpacing(8)
        for field_name, label_text in _BUYER_FIELDS:
            edit = self._make_edit()
            self._fields[field_name] = edit
            buyer_form.addRow(self._make_label(label_text), edit)
        form_layout.addLayout(buyer_form)

        # Seller section
        form_layout.addWidget(_SectionHeader("销售方"))
        seller_form = QFormLayout()
        seller_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        seller_form.setHorizontalSpacing(16)
        seller_form.setVerticalSpacing(8)
        for field_name, label_text in _SELLER_FIELDS:
            edit = self._make_edit()
            self._fields[field_name] = edit
            seller_form.addRow(self._make_label(label_text), edit)
        form_layout.addLayout(seller_form)

        # Amount section
        form_layout.addWidget(_SectionHeader("金额"))
        amount_form = QFormLayout()
        amount_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        amount_form.setHorizontalSpacing(16)
        amount_form.setVerticalSpacing(8)
        for field_name, label_text in _AMOUNT_FIELDS:
            edit = self._make_edit()
            if field_name in _DECIMAL_FIELDS:
                edit.setStyleSheet(
                    edit.styleSheet() + f"font-weight: 600; font-size: 14px;"
                )
            self._fields[field_name] = edit
            amount_form.addRow(self._make_label(label_text), edit)
        form_layout.addLayout(amount_form)

        form_layout.addStretch()
        scroll.setWidget(form_container)
        outer.addWidget(scroll, 1)

        # ── bottom action bar ──
        action_bar = QFrame(self)
        action_bar.setFixedHeight(60)
        action_bar.setStyleSheet(
            f"background: {COLORS['bg_surface']}; border-top: 1px solid {COLORS['border']};"
        )
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(24, 0, 24, 0)

        save_btn = QPushButton("💾 保存修改", self)
        save_btn.setProperty("btn-style", "secondary")
        save_btn.setStyleSheet(
            f"background: {COLORS['bg_surface']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; "
            f"padding: 9px 22px; font-size: 13px; font-weight: 500; min-width: 80px;"
        )
        save_btn.clicked.connect(self._on_save)

        export_btn = QPushButton("📊 导出 Excel", self)
        export_btn.setStyleSheet(
            f"background: {COLORS['primary']}; color: #FFFFFF; "
            f"border: none; border-radius: 6px; "
            f"padding: 9px 22px; font-size: 13px; font-weight: 600; min-width: 80px;"
        )
        export_btn.clicked.connect(self.export_requested)

        action_layout.addStretch()
        action_layout.addWidget(save_btn)
        action_layout.addSpacing(12)
        action_layout.addWidget(export_btn)
        outer.addWidget(action_bar)

    # ── helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _make_label(text: str) -> QLabel:
        lbl = QLabel(text + "：")
        lbl.setStyleSheet(
            f"font-size: 13px; color: {COLORS['text_secondary']}; "
            f"min-width: 80px;"
        )
        return lbl

    @staticmethod
    def _make_edit() -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText("未识别")
        edit.setFixedHeight(36)
        return edit

    # ── public ────────────────────────────────────────────────────────
    def show_invoice(self, invoice: Invoice) -> None:
        self._invoice = invoice
        for field_name, edit in self._fields.items():
            value = getattr(invoice, field_name, "")
            edit.setText(str(value) if value else "")

        # status badge
        status_map = {
            InvoiceStatus.PENDING: ("待处理", COLORS["text_muted"], COLORS["bg_app"]),
            InvoiceStatus.PROCESSING: ("识别中", COLORS["info"], COLORS["info_bg"]),
            InvoiceStatus.SUCCESS: ("已完成", COLORS["success"], COLORS["success_bg"]),
            InvoiceStatus.REVIEW: ("需复核", COLORS["warning"], COLORS["warning_bg"]),
            InvoiceStatus.FAILED: ("失败", COLORS["danger"], COLORS["danger_bg"]),
        }
        text, color, bg = status_map.get(invoice.status, status_map[InvoiceStatus.PENDING])
        self._status_badge.setText(text)
        self._status_badge.setStyleSheet(
            f"color: {color}; background: {bg}; border-radius: 12px; "
            f"padding: 2px 12px; font-size: 11px; font-weight: 600;"
        )
        self._status_badge.setVisible(True)

        if invoice.status == InvoiceStatus.FAILED and invoice.error_message:
            # highlight error fields
            pass  # could add error display later

    def clear(self) -> None:
        self._invoice = None
        self._status_badge.setVisible(False)
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
