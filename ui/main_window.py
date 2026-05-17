import os
import concurrent.futures
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QListWidget, QListWidgetItem, QToolBar,
    QStatusBar, QFileDialog, QMessageBox, QSplitter, QLabel,
    QWidget, QHBoxLayout, QVBoxLayout, QFrame, QSizePolicy,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QFont, QIcon
from models.invoice import Invoice, InvoiceStatus
from core.ocr_engine import OcrEngine
from core.invoice_parser import InvoiceParser
from core.exporter import Exporter, ExportMode
from ui.preview_panel import PreviewPanel
from ui.theme import COLORS

_STATUS_ICONS = {
    InvoiceStatus.PENDING:    "⏳",
    InvoiceStatus.PROCESSING: "🔄",
    InvoiceStatus.SUCCESS:    "✅",
    InvoiceStatus.REVIEW:     "⚠️",
    InvoiceStatus.FAILED:     "❌",
}

_STATUS_STYLES: dict[str, dict] = {
    InvoiceStatus.PENDING: {
        "text": "等待",
        "color": COLORS["text_muted"],
        "bg": COLORS["bg_app"],
    },
    InvoiceStatus.PROCESSING: {
        "text": "识别中",
        "color": COLORS["info"],
        "bg": COLORS["info_bg"],
    },
    InvoiceStatus.SUCCESS: {
        "text": "完成",
        "color": COLORS["success"],
        "bg": COLORS["success_bg"],
    },
    InvoiceStatus.REVIEW: {
        "text": "需复核",
        "color": COLORS["warning"],
        "bg": COLORS["warning_bg"],
    },
    InvoiceStatus.FAILED: {
        "text": "失败",
        "color": COLORS["danger"],
        "bg": COLORS["danger_bg"],
    },
}


class _FileListItem(QWidget):
    def __init__(self, filename: str, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 6, 12, 6)
        main_layout.setSpacing(4)

        # top row: filename + status badge
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self._name_label = QLabel(self)
        self._name_label.setStyleSheet(f"font-size: 13px; color: {COLORS['text_primary']};")

        self._status_badge = QLabel(self)
        self._status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_badge.setFixedHeight(24)
        self._status_badge.setMinimumWidth(56)

        top_row.addWidget(self._name_label)
        top_row.addStretch()
        top_row.addWidget(self._status_badge)

        # bottom row: progress bar + percentage label
        progress_row = QHBoxLayout()
        progress_row.setSpacing(6)

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)

        self._progress_label = QLabel(self)
        self._progress_label.setFixedWidth(36)
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._progress_label.setStyleSheet(f"font-size: 11px; color: {COLORS['info']}; font-weight: 600;")

        progress_row.addWidget(self._progress_bar)
        progress_row.addWidget(self._progress_label)

        main_layout.addLayout(top_row)
        main_layout.addLayout(progress_row)

        self._progress_row_visible = False
        self._list_item: QListWidgetItem | None = None
        self._set_progress_visible(False)
        self.update_status(filename, InvoiceStatus.PENDING)

    def set_list_item(self, item: QListWidgetItem) -> None:
        """Store reference to the owning QListWidgetItem for size updates."""
        self._list_item = item

    def _set_progress_visible(self, visible: bool) -> None:
        self._progress_bar.setVisible(visible)
        self._progress_label.setVisible(visible)
        self._progress_row_visible = visible
        if self._list_item is not None:
            self._list_item.setSizeHint(self.sizeHint())

    def update_status(self, filename: str, status: str) -> None:
        icon = _STATUS_ICONS.get(status, "⏳")
        self._name_label.setText(f"{icon}  {filename}")

        style = _STATUS_STYLES.get(status, _STATUS_STYLES[InvoiceStatus.PENDING])
        self._status_badge.setText(style["text"])
        self._status_badge.setStyleSheet(
            f"color: {style['color']}; background: {style['bg']}; "
            f"border-radius: 12px; padding: 2px 10px; font-size: 11px; font-weight: 600;"
        )

        # hide progress when not processing
        if status != InvoiceStatus.PROCESSING:
            self._set_progress_visible(False)

    def update_progress(self, percent: int) -> None:
        """Update the progress bar and percentage label (0-100)."""
        self._set_progress_visible(True)
        self._progress_bar.setValue(min(max(percent, 0), 100))
        self._progress_label.setText(f"{percent}%")


class _EmptyState(QWidget):
    """Placeholder shown when no files are loaded."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("📄", self)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 48px;")

        title = QLabel("拖拽发票文件到此处", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {COLORS['text_secondary']};")

        subtitle = QLabel("或使用工具栏添加 PDF / PNG 文件", self)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"font-size: 12px; color: {COLORS['text_muted']}; margin-top: 4px;")

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(subtitle)


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
    file_progress = pyqtSignal(int, int)  # (row, percent 0-100)
    invoice_done = pyqtSignal(int, Invoice)
    finished = pyqtSignal()

    def __init__(self, file_paths: list[str],
                 row_indices: list[int] | None = None,
                 max_workers: int = 3):
        super().__init__()
        self._file_paths = file_paths
        self._row_indices = row_indices
        self._max_workers = max_workers
        self._cancelled = False

    def cancel(self) -> None:
        logging.info("Worker: cancel requested")
        self._cancelled = True

    def _process_file(self, i: int, path: str, row: int) -> None:
        if self._cancelled:
            return
        self.progress.emit(row, os.path.basename(path))
        self.file_progress.emit(row, 0)
        try:
            engine = OcrEngine()
            parser = InvoiceParser()
            texts = engine.extract_text_from_file(
                path,
                progress_callback=lambda pct, r=row: self.file_progress.emit(r, pct),
            )
            invoice = parser.parse(texts, source_file=os.path.basename(path))
            logging.info("File %d done, status=%s", i, invoice.status)
        except Exception as exc:
            logging.exception("Error processing file %d: %s", i, path)
            invoice = Invoice(
                source_file=os.path.basename(path),
                status=InvoiceStatus.FAILED,
                error_message=str(exc),
            )
        self.invoice_done.emit(row, invoice)

    def run(self) -> None:
        logging.info("Worker.run started, files=%s", self._file_paths)
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=self._max_workers) as executor:
            futures = []
            for i, path in enumerate(self._file_paths):
                if self._cancelled:
                    break
                row = self._row_indices[i] if self._row_indices else i
                futures.append(executor.submit(self._process_file, i, path, row))
            concurrent.futures.wait(futures)
        logging.info("Worker.run finished")
        self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("发票扫描识别系统")
        self.setMinimumSize(1100, 680)
        self.resize(1280, 760)
        self.setAcceptDrops(True)
        self._file_paths: list[str] = []
        self._invoices: list[Invoice] = []
        self._item_widgets: list[_FileListItem] = []
        self._setup_ui()

    # ── UI construction ───────────────────────────────────────────────
    def _setup_ui(self) -> None:
        # --- toolbar ---
        toolbar = QToolBar(self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        for label, slot in [("选择文件", self._on_add_files),
                             ("选择文件夹", self._on_add_folder)]:
            act = QAction(label, self)
            act.triggered.connect(slot)
            toolbar.addAction(act)

        toolbar.addSeparator()

        clear_act = QAction("清空列表", self)
        clear_act.setProperty("action-danger", True)
        clear_act.triggered.connect(self._on_clear)
        toolbar.addAction(clear_act)

        self._cancel_act = QAction("✕ 取消识别", self)
        self._cancel_act.setProperty("action-danger", True)
        self._cancel_act.triggered.connect(self._on_cancel)
        self._cancel_act.setVisible(False)
        toolbar.addAction(self._cancel_act)

        # --- main content ---
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.setCentralWidget(splitter)

        # left: file panel
        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # panel header
        header = QFrame(self)
        header.setFixedHeight(44)
        header.setStyleSheet(
            f"background: {COLORS['bg_surface']}; border-bottom: 1px solid {COLORS['border']};"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_label = QLabel("📋 文件列表", self)
        header_label.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {COLORS['text_primary']};"
        )
        self._count_badge = QLabel("0", self)
        self._count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_badge.setFixedSize(28, 20)
        self._count_badge.setStyleSheet(
            f"background: {COLORS['primary_light']}; color: {COLORS['primary']}; "
            f"border-radius: 10px; font-size: 11px; font-weight: 700;"
        )
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(self._count_badge)
        left_layout.addWidget(header)

        # file list
        self._file_list = QListWidget(self)
        self._file_list.currentRowChanged.connect(self._on_file_selected)
        left_layout.addWidget(self._file_list)

        # empty state overlay
        self._empty_state = _EmptyState(self)
        self._empty_state.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(self._empty_state)
        self._empty_state.setVisible(True)
        self._file_list.setVisible(False)

        splitter.addWidget(left_panel)

        # right: preview
        self._preview = PreviewPanel(self)
        self._preview.invoice_changed.connect(self._on_invoice_changed)
        self._preview.export_requested.connect(self._on_export)
        splitter.addWidget(self._preview)
        splitter.setSizes([380, 900])

        # --- status bar ---
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        self._stats_label = QLabel(self)
        self._stats_label.setStyleSheet("padding: 0 8px;")
        status_bar.addWidget(self._stats_label)
        self._update_stats()

    # ── Drag & Drop ───────────────────────────────────────────────────
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

    # ── File management ───────────────────────────────────────────────
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
        self._file_paths.clear()
        self._invoices.clear()
        self._item_widgets.clear()
        self._file_list.clear()
        self._preview.clear()
        self._update_stats()
        self._empty_state.setVisible(True)
        self._file_list.setVisible(False)

    def _add_files(self, paths: list[str]) -> None:
        existing = set(self._file_paths)
        added = False
        for path in paths:
            if path not in existing:
                self._file_paths.append(path)
                self._invoices.append(Invoice(source_file=os.path.basename(path)))
                filename = os.path.basename(path)
                item = QListWidgetItem()
                widget = _FileListItem(filename)
                widget.set_list_item(item)
                item.setSizeHint(widget.sizeHint())
                self._file_list.addItem(item)
                self._file_list.setItemWidget(item, widget)
                self._item_widgets.append(widget)
                added = True
        if self._file_paths:
            self._empty_state.setVisible(False)
            self._file_list.setVisible(True)
        self._update_stats()
        if added:
            self._auto_start_ocr()

    def _on_file_selected(self, row: int) -> None:
        if 0 <= row < len(self._invoices):
            self._preview.show_invoice(self._invoices[row])

    def _on_invoice_changed(self, invoice: Invoice) -> None:
        row = self._file_list.currentRow()
        if 0 <= row < len(self._invoices) and row < len(self._item_widgets):
            self._invoices[row] = invoice
            self._item_widgets[row].update_status(invoice.source_file, invoice.status)

    # ── OCR ───────────────────────────────────────────────────────────
    def _auto_start_ocr(self) -> None:
        """Auto-start OCR for pending files. If OCR is already running, skip —
        _on_ocr_finished will check again for any newly added pending files."""
        if hasattr(self, "_thread") and self._thread.isRunning():
            return
        self._start_ocr_for_pending()

    def _start_ocr_for_pending(self) -> None:
        """Collect all PENDING invoices and start an OCR worker for them."""
        pending_indices = [i for i, inv in enumerate(self._invoices)
                          if inv.status == InvoiceStatus.PENDING]
        if not pending_indices:
            return
        pending_paths = [self._file_paths[i] for i in pending_indices]
        self._cancel_act.setVisible(True)
        self._worker = _OcrWorker(pending_paths, pending_indices)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_ocr_progress)
        self._worker.file_progress.connect(self._on_file_progress)
        self._worker.invoice_done.connect(self._on_invoice_done)
        self._worker.finished.connect(self._on_ocr_finished)
        self._thread.start()

    def _on_cancel(self) -> None:
        if hasattr(self, "_worker"):
            self._worker.cancel()

    def _on_ocr_progress(self, row: int, filename: str) -> None:
        if 0 <= row < len(self._item_widgets):
            self._item_widgets[row].update_status(filename, InvoiceStatus.PROCESSING)

    def _on_file_progress(self, row: int, percent: int) -> None:
        """Update per-file progress bar."""
        if 0 <= row < len(self._item_widgets):
            self._item_widgets[row].update_progress(percent)

    def _on_invoice_done(self, row: int, invoice: Invoice) -> None:
        if 0 <= row < len(self._invoices):
            self._invoices[row] = invoice
            if row < len(self._item_widgets):
                self._item_widgets[row].update_status(invoice.source_file, invoice.status)
        if self._file_list.currentRow() == row:
            self._preview.show_invoice(invoice)
        self._update_stats()

    def _on_ocr_finished(self) -> None:
        logging.info("_on_ocr_finished: start")
        self._thread.quit()
        self._thread.wait(3000)
        self._cancel_act.setVisible(False)
        for invoice, widget in zip(self._invoices, self._item_widgets):
            widget.update_status(invoice.source_file, invoice.status)
        self._update_stats()
        # If more pending files were added while we were running, auto-continue
        pending = any(inv.status == InvoiceStatus.PENDING for inv in self._invoices)
        if pending:
            self._start_ocr_for_pending()
        logging.info("_on_ocr_finished: after update_stats")
        duplicates = _find_duplicates(self._invoices)
        if duplicates:
            msg = "检测到重复发票：\n" + "\n".join(
                f"发票代码 {code}  号码 {num}" for code, num in duplicates
            )
            QMessageBox.warning(self, "重复发票提示", msg)

    # ── Export ────────────────────────────────────────────────────────
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
            removed = Exporter().export(self._invoices, path, mode)
            logging.info("Export succeeded: %s", path)
            msg = f"已保存到：{path}"
            if removed > 0:
                msg += f"\n\n已自动去重 {removed} 张重复发票（保留最后一条）"
            QMessageBox.information(self, "导出成功", msg)
        except PermissionError:
            logging.error("Export failed (PermissionError): %s", path)
            QMessageBox.critical(self, "导出失败", f"文件被占用，请关闭 {path} 后重试")
        except Exception as exc:
            logging.exception("Export failed: %s", path)
            QMessageBox.critical(self, "导出失败", str(exc))

    # ── Stats ─────────────────────────────────────────────────────────
    def _update_stats(self) -> None:
        total   = len(self._invoices)
        success = sum(1 for i in self._invoices if i.status == InvoiceStatus.SUCCESS)
        review  = sum(1 for i in self._invoices if i.status == InvoiceStatus.REVIEW)
        failed  = sum(1 for i in self._invoices if i.status == InvoiceStatus.FAILED)

        self._count_badge.setText(str(total))

        parts = [f"总计 <b>{total}</b>"]
        if success:
            parts.append(f"<span style='color:{COLORS['success']}'>✓ 完成 {success}</span>")
        if review:
            parts.append(f"<span style='color:{COLORS['warning']}'>⚠ 复核 {review}</span>")
        if failed:
            parts.append(f"<span style='color:{COLORS['danger']}'>✗ 失败 {failed}</span>")
        self._stats_label.setText("　　".join(parts))
