import os
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QListWidget, QListWidgetItem, QToolBar,
    QStatusBar, QFileDialog, QMessageBox, QSplitter, QLabel,
)
from PyQt6.QtCore import Qt, QThread, QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent
from models.invoice import Invoice, InvoiceStatus
from core.ocr_engine import OcrEngine
from core.invoice_parser import InvoiceParser
from core.exporter import Exporter, ExportMode
from ui.preview_panel import PreviewPanel
from ui.progress_dialog import ProgressDialog

_STATUS_ICONS = {
    InvoiceStatus.PENDING:    "○",
    InvoiceStatus.PROCESSING: "…",
    InvoiceStatus.SUCCESS:    "✓",
    InvoiceStatus.REVIEW:     "⚠",
    InvoiceStatus.FAILED:     "✗",
}


def _find_duplicates(invoices: list[Invoice]) -> list[tuple[str, str]]:
    seen: dict[tuple[str, str], bool] = {}
    duplicates: list[tuple[str, str]] = []
    for inv in invoices:
        if not inv.invoice_code or not inv.invoice_number:
            continue
        key = (inv.invoice_code, inv.invoice_number)
        if key in seen:
            if key not in duplicates:
                duplicates.append(key)
        else:
            seen[key] = True
    return duplicates


class _OcrWorker(QObject):
    progress = pyqtSignal(int, str)
    invoice_done = pyqtSignal(int, Invoice)
    finished = pyqtSignal()
    model_status = pyqtSignal(str)

    def __init__(self, file_paths: list[str]):
        super().__init__()
        self._file_paths = file_paths
        self._cancelled = False

    def cancel(self) -> None:
        logging.info("Worker: cancel requested")
        self._cancelled = True

    def run(self) -> None:
        logging.info("Worker.run started, files=%s", self._file_paths)
        try:
            engine = OcrEngine()
        except Exception as exc:
            logging.exception("OcrEngine init failed")
            for i, path in enumerate(self._file_paths):
                self.invoice_done.emit(i, Invoice(
                    source_file=os.path.basename(path),
                    status=InvoiceStatus.FAILED,
                    error_message=f"OCR引擎初始化失败：{exc}",
                ))
            self.finished.emit()
            return
        logging.info("OcrEngine ready")
        self.model_status.emit("")  # 初始化完成，切换到文件处理模式
        parser = InvoiceParser()
        for i, path in enumerate(self._file_paths):
            if self._cancelled:
                break
            logging.info("Processing file %d: %s", i, path)
            self.progress.emit(i + 1, os.path.basename(path))
            try:
                texts = engine.extract_text_from_file(path)
                invoice = parser.parse(texts, source_file=os.path.basename(path))
                logging.info("File %d done, status=%s", i, invoice.status)
            except Exception as exc:
                logging.exception("Error processing file %d: %s", i, path)
                invoice = Invoice(
                    source_file=os.path.basename(path),
                    status=InvoiceStatus.FAILED,
                    error_message=str(exc),
                )
            self.invoice_done.emit(i, invoice)
        logging.info("Worker.run finished")
        self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("发票扫描识别系统")
        self.setMinimumSize(1000, 600)
        self.setAcceptDrops(True)
        self._file_paths: list[str] = []
        self._invoices: list[Invoice] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        toolbar = QToolBar(self)
        self.addToolBar(toolbar)
        for label, slot in [("选择文件", self._on_add_files),
                             ("选择文件夹", self._on_add_folder),
                             ("清空列表", self._on_clear)]:
            act = QAction(label, self)
            act.triggered.connect(slot)
            toolbar.addAction(act)
        toolbar.addSeparator()
        start_act = QAction("开始识别", self)
        start_act.triggered.connect(self._on_start_ocr)
        toolbar.addAction(start_act)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.setCentralWidget(splitter)

        self._file_list = QListWidget(self)
        self._file_list.currentRowChanged.connect(self._on_file_selected)
        splitter.addWidget(self._file_list)

        self._preview = PreviewPanel(self)
        self._preview.invoice_changed.connect(self._on_invoice_changed)
        self._preview.export_requested.connect(self._on_export)
        splitter.addWidget(self._preview)
        splitter.setSizes([350, 650])

        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        self._stats_label = QLabel("文件数: 0", self)
        status_bar.addWidget(self._stats_label)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                paths += [os.path.join(path, f) for f in os.listdir(path)
                          if f.lower().endswith(('.pdf', '.png'))]
            elif path.lower().endswith(('.pdf', '.png')):
                paths.append(path)
        self._add_files(paths)

    def _on_add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "选择发票文件", "", "发票文件 (*.pdf *.png)")
        self._add_files(paths)

    def _on_add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            paths = [os.path.join(folder, f) for f in os.listdir(folder)
                     if f.lower().endswith(('.pdf', '.png'))]
            self._add_files(paths)

    def _on_clear(self) -> None:
        logging.info("File list cleared (%d files)", len(self._file_paths))
        self._file_paths.clear()
        self._invoices.clear()
        self._file_list.clear()
        self._preview.clear()
        self._update_stats()

    def _add_files(self, paths: list[str]) -> None:
        existing = set(self._file_paths)
        added = 0
        for path in paths:
            if path not in existing:
                self._file_paths.append(path)
                self._invoices.append(Invoice(source_file=os.path.basename(path)))
                icon = _STATUS_ICONS[InvoiceStatus.PENDING]
                self._file_list.addItem(QListWidgetItem(f"{icon} {os.path.basename(path)}"))
                added += 1
        if added:
            logging.info("Added %d file(s), total=%d", added, len(self._file_paths))
        self._update_stats()

    def _on_file_selected(self, row: int) -> None:
        if 0 <= row < len(self._invoices):
            self._preview.show_invoice(self._invoices[row])

    def _on_invoice_changed(self, invoice: Invoice) -> None:
        row = self._file_list.currentRow()
        if 0 <= row < len(self._invoices):
            self._invoices[row] = invoice
            icon = _STATUS_ICONS.get(invoice.status, "○")
            self._file_list.item(row).setText(f"{icon} {invoice.source_file}")

    def _on_start_ocr(self) -> None:
        if not self._file_paths:
            QMessageBox.information(self, "提示", "请先添加发票文件")
            return
        logging.info("OCR started: %d file(s)", len(self._file_paths))
        self._progress_dlg = ProgressDialog(len(self._file_paths), self)
        self._worker = _OcrWorker(self._file_paths)
        self._thread = QThread()  # 无父对象，由 deleteLater 管理生命周期
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.model_status.connect(self._on_model_status)
        self._worker.progress.connect(self._on_ocr_progress)
        self._worker.invoice_done.connect(self._on_invoice_done)
        self._worker.finished.connect(self._on_ocr_finished)
        # Qt 标准清理模式：让信号驱动线程退出和对象销毁，避免主线程 wait() 阻塞崩溃
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._progress_dlg.rejected.connect(self._worker.cancel)
        # 用 singleShot(0) 确保 exec() 先建好事件循环再启动线程，
        # 避免 RapidOCR 过快完成时信号堆积导致弹窗"闪退"
        QTimer.singleShot(0, self._thread.start)
        self._progress_dlg.exec()

    def _on_model_status(self, message: str) -> None:
        if message:
            self._progress_dlg.set_loading_model(message)
        else:
            self._progress_dlg.set_processing()

    def _on_ocr_progress(self, current: int, filename: str) -> None:
        self._progress_dlg.update_progress(current, filename)
        item = self._file_list.item(current - 1)
        if item:
            item.setText(f"{_STATUS_ICONS[InvoiceStatus.PROCESSING]} {filename}")

    def _on_invoice_done(self, row: int, invoice: Invoice) -> None:
        self._invoices[row] = invoice
        item = self._file_list.item(row)
        if item:
            icon = _STATUS_ICONS.get(invoice.status, "○")
            item.setText(f"{icon} {invoice.source_file}")
        if self._file_list.currentRow() == row:
            self._preview.show_invoice(invoice)
        self._update_stats()

    def _on_ocr_finished(self) -> None:
        success = sum(1 for i in self._invoices if i.status == InvoiceStatus.SUCCESS)
        review  = sum(1 for i in self._invoices if i.status == InvoiceStatus.REVIEW)
        failed  = sum(1 for i in self._invoices if i.status == InvoiceStatus.FAILED)
        logging.info("OCR finished: total=%d success=%d review=%d failed=%d",
                     len(self._invoices), success, review, failed)
        self._progress_dlg.close()
        self._update_stats()
        duplicates = _find_duplicates(self._invoices)
        if duplicates:
            logging.warning("Duplicate invoices detected: %s", duplicates)
            msg = "检测到重复发票：\n" + "\n".join(
                f"发票代码 {code}  号码 {num}" for code, num in duplicates
            )
            QMessageBox.warning(self, "重复发票提示", msg)

    def _on_export(self) -> None:
        if not self._invoices:
            QMessageBox.information(self, "提示", "没有可导出的数据")
            return
        reply = QMessageBox.question(
            self, "导出模式",
            "点击[是]→汇总模式（每张发票一行）\n点击[否]→明细模式（每条明细一行）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        mode = ExportMode.SUMMARY if reply == QMessageBox.StandardButton.Yes else ExportMode.DETAIL
        path, _ = QFileDialog.getSaveFileName(self, "保存 Excel", "", "Excel 文件 (*.xlsx)")
        if not path:
            return
        logging.info("Export: mode=%s path=%s invoices=%d", mode.name, path, len(self._invoices))
        try:
            Exporter().export(self._invoices, path, mode)
            logging.info("Export succeeded: %s", path)
            QMessageBox.information(self, "导出成功", f"已保存到：{path}")
        except PermissionError:
            logging.error("Export failed (PermissionError): %s", path)
            QMessageBox.critical(self, "导出失败", f"文件被占用，请关闭 {path} 后重试")
        except Exception as exc:
            logging.exception("Export failed: %s", path)
            QMessageBox.critical(self, "导出失败", str(exc))

    def _update_stats(self) -> None:
        total   = len(self._invoices)
        success = sum(1 for i in self._invoices if i.status == InvoiceStatus.SUCCESS)
        review  = sum(1 for i in self._invoices if i.status == InvoiceStatus.REVIEW)
        failed  = sum(1 for i in self._invoices if i.status == InvoiceStatus.FAILED)
        self._stats_label.setText(
            f"文件数: {total}   已完成: {success}   需复核: {review}   失败: {failed}"
        )
