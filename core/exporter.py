from enum import Enum
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
