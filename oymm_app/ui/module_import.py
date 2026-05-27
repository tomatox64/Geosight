"""模块1: 数据导入 - UI 页面."""
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QProgressBar, QTextEdit, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QSplitter,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from oymm_app.modules.data_import import DataImporter, ImportResult, PhotoInfo, LidarInfo


class _ScanWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, directory: str):
        super().__init__()
        self.directory = directory

    def run(self):
        try:
            result = DataImporter.scan_directory(self.directory)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DataImportPage(QWidget):
    """Data import module page."""

    data_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._result: ImportResult | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Title
        title = QLabel("数据导入")
        title.setProperty("cssClass", "titleLabel")
        layout.addWidget(title)

        desc = QLabel("支持 RGB 倾斜摄影影像、LiDAR 点云 (.las/.laz)、多光谱影像 (.tif) 的批量导入。")
        desc.setProperty("cssClass", "subtitleLabel")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_scan = QPushButton("选择目录并扫描")
        self.btn_scan.setProperty("cssClass", "runButton")
        self.btn_scan.clicked.connect(self._on_scan)
        toolbar.addWidget(self.btn_scan)

        self.btn_clear = QPushButton("清除")
        self.btn_clear.setEnabled(False)
        self.btn_clear.clicked.connect(self._on_clear)
        toolbar.addWidget(self.btn_clear)
        toolbar.addStretch()

        self.lbl_status = QLabel("")
        self.lbl_status.setProperty("cssClass", "statusLabel")
        toolbar.addWidget(self.lbl_status)
        layout.addLayout(toolbar)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Content area: two panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: summary + table
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.summary_box = QGroupBox("扫描结果")
        self.summary_box.setVisible(False)
        summary_layout = QVBoxLayout(self.summary_box)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(100)
        self.summary_text.setStyleSheet("background: #161b22; font-size: 11pt;")
        summary_layout.addWidget(self.summary_text)
        left_layout.addWidget(self.summary_box)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["文件名", "类型", "尺寸/点数", "大小"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableWidget { gridline-color: #ddd; }"
            "QTableWidget::item { padding: 4px 12px; }"
        )
        self.table.setVisible(False)
        left_layout.addWidget(self.table)

        splitter.addWidget(left)

        # Right: detail / preview placeholder
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_detail = QGroupBox("文件详情")
        detail_layout = QVBoxLayout(right_detail)
        self.detail_text = QLabel("选择左侧文件查看详情")
        self.detail_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_text.setStyleSheet("color: #999; font-size: 11pt;")
        self.detail_text.setWordWrap(True)
        detail_layout.addWidget(self.detail_text)
        right_layout.addWidget(right_detail)

        splitter.addWidget(right)
        splitter.setSizes([280, 180])

        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(splitter, stretch=1)

        # Bottom action bar
        bottom = QHBoxLayout()
        bottom.addStretch()
        self.btn_next = QPushButton("确认导入，进入质控 →")
        self.btn_next.setEnabled(False)
        self.btn_next.setProperty("cssClass", "nextButton")
        self.btn_next.clicked.connect(self._on_confirm)
        bottom.addWidget(self.btn_next)
        layout.addLayout(bottom)

    def _on_scan(self):
        directory = QFileDialog.getExistingDirectory(
            self, "选择数据目录", "E:/oymm/data"
        )
        if not directory:
            return

        self.btn_scan.setEnabled(False)
        self.progress.setVisible(True)
        self.lbl_status.setText("扫描中...")

        self._worker = _ScanWorker(directory)
        self._worker.finished.connect(self._on_scan_done)
        self._worker.error.connect(self._on_scan_error)
        self._worker.start()

    def _on_scan_done(self, result: ImportResult):
        self._result = result
        self.btn_scan.setEnabled(True)
        self.progress.setVisible(False)

        if result.total_files == 0:
            self.lbl_status.setText("未检测到支持的数据文件")
            QMessageBox.information(self, "提示", f"未检测到支持的数据文件。\n{chr(10).join(result.errors or [''])}")
            return

        self.lbl_status.setText(result.summary)
        self.summary_box.setVisible(True)
        self.summary_text.setPlainText(
            f"{result.summary}\n"
            f"总计: {result.total_files} 个文件"
        )
        if result.errors:
            self.summary_text.append(f"\n警告: {len(result.errors)} 个文件无法识别")

        self._populate_table(result)
        self.btn_clear.setEnabled(True)
        self.btn_next.setEnabled(True)

    def _on_scan_error(self, msg: str):
        self.btn_scan.setEnabled(True)
        self.progress.setVisible(False)
        self.lbl_status.setText(f"错误: {msg}")
        QMessageBox.critical(self, "扫描错误", msg)

    def _populate_table(self, result: ImportResult):
        rows = len(result.rgb) + len(result.lidar) + len(result.multispectral)
        self.table.setRowCount(rows)
        self.table.setVisible(True)

        row = 0
        # RGB
        for p in result.rgb:
            self._set_row(row, p.path.name, "RGB影像",
                          f"{p.width}×{p.height}", f"{p.size_mb} MB", p)
            row += 1
        # LiDAR
        for l in result.lidar:
            self._set_row(row, l.path.name, "LiDAR 点云",
                          f"{l.point_count:,} 点", f"{l.size_mb} MB", l)
            row += 1
        # Multispectral
        for m in result.multispectral:
            self._set_row(row, m.path.name, "多光谱",
                          f"{m.bands}波段 {m.width}×{m.height}", "", m)
            row += 1

    def _set_row(self, row: int, name: str, dtype: str, info: str, size: str, data):
        self.table.setItem(row, 0, QTableWidgetItem(name))
        self.table.setItem(row, 1, QTableWidgetItem(dtype))
        self.table.setItem(row, 2, QTableWidgetItem(info))
        self.table.setItem(row, 3, QTableWidgetItem(size))

    def _on_selection_changed(self):
        idx = self.table.currentRow()
        if idx < 0 or self._result is None:
            self.detail_text.setText("选择左侧文件查看详情")
            return

        all_data = (self._result.rgb + self._result.lidar +
                    self._result.multispectral)
        if idx < len(all_data):
            item = all_data[idx]
            if isinstance(item, PhotoInfo):
                self.detail_text.setText(
                    f"文件: {item.path.name}\n"
                    f"类型: RGB 影像\n"
                    f"分辨率: {item.width} × {item.height}\n"
                    f"大小: {item.size_mb} MB\n"
                    f"路径: {item.path}"
                )
            elif isinstance(item, LidarInfo):
                self.detail_text.setText(
                    f"文件: {item.path.name}\n"
                    f"类型: LiDAR 点云\n"
                    f"点数: {item.point_count:,}\n"
                    f"大小: {item.size_mb} MB\n"
                    f"路径: {item.path}"
                )
            else:
                self.detail_text.setText(
                    f"文件: {item.path.name}\n"
                    f"类型: 多光谱影像\n"
                    f"波段: {item.bands}\n"
                    f"分辨率: {item.width} × {item.height}"
                )

    def _on_clear(self):
        self._result = None
        self.table.setRowCount(0)
        self.table.setVisible(False)
        self.summary_box.setVisible(False)
        self.btn_clear.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.detail_text.setText("选择左侧文件查看详情")
        self.lbl_status.setText("")

    def _on_confirm(self):
        if self._result:
            self.data_ready.emit(self._result)
