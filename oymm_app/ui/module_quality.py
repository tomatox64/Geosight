"""模块2: 智能质控 - UI 页面."""
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QSplitter, QTextEdit, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from oymm_app.modules.quality_control import QualityController, QualityReport, PhotoQuality


class _QCWorker(QThread):
    finished = pyqtSignal(object)
    progress = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, photo_paths: list[Path]):
        super().__init__()
        self.photo_paths = photo_paths

    def run(self):
        try:
            self.progress.emit(10)
            report = QualityController.analyze_photos(self.photo_paths)
            self.progress.emit(100)
            self.finished.emit(report)
        except Exception as e:
            self.error.emit(str(e))


class QualityControlPage(QWidget):
    """Smart quality control module page."""

    data_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._report: QualityReport | None = None
        self._photo_paths: list[Path] = []
        self._setup_ui()

    def load_photos(self, paths: list[Path]):
        self._photo_paths = paths
        self._run_analysis()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Title
        title = QLabel("智能质控")
        title.setProperty("cssClass", "titleLabel")
        layout.addWidget(title)

        desc = QLabel("自动检测照片质量：模糊度、曝光、分辨率、重叠度估算。")
        desc.setProperty("cssClass", "subtitleLabel")
        layout.addWidget(desc)

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_run = QPushButton("开始分析")
        self.btn_run.setProperty("cssClass", "runButton")
        self.btn_run.clicked.connect(self._run_analysis)
        toolbar.addWidget(self.btn_run)

        self.lbl_status = QLabel("等待数据...")
        self.lbl_status.setProperty("cssClass", "statusLabel")
        toolbar.addWidget(self.lbl_status)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMaximum(100)
        layout.addWidget(self.progress)

        # Score cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        self.cards = {}
        for key, label in [("pass", "通过率"), ("score", "综合评分"),
                           ("blur", "模糊"), ("exposure", "曝光")]:
            card = QFrame()
            card.setStyleSheet(
                "QFrame{background:#161b22;border-radius:6px;padding:6px;border:1px solid #30363d;}"
            )
            cl = QVBoxLayout(card)
            val_label = QLabel("--")
            val_label.setStyleSheet("font-size: 22pt; font-weight: bold; color: #c9d1d9;")
            val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label = QLabel(label)
            name_label.setStyleSheet("font-size: 9pt; color: #8b949e;")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(val_label)
            cl.addWidget(name_label)
            cards_layout.addWidget(card)
            self.cards[key] = val_label
        self.cards_frame = QWidget()
        self.cards_frame.setLayout(cards_layout)
        self.cards_frame.setVisible(False)
        layout.addWidget(self.cards_frame)

        # Content splitter
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top: QC table
        table_group = QGroupBox("照片质量详情")
        table_layout = QVBoxLayout(table_group)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["文件名", "模糊度", "曝光均值", "分辨率", "状态"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table_layout.addWidget(self.table)
        splitter.addWidget(table_group)

        # Bottom: overlap info + issues
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        overlap_group = QGroupBox("重叠度估算")
        ov_layout = QVBoxLayout(overlap_group)
        self.overlap_text = QLabel("等待分析...")
        self.overlap_text.setWordWrap(True)
        self.overlap_text.setStyleSheet("font-size: 11pt; padding: 8px;")
        ov_layout.addWidget(self.overlap_text)
        bottom_layout.addWidget(overlap_group)

        issues_group = QGroupBox("问题汇总")
        is_layout = QVBoxLayout(issues_group)
        self.issues_text = QTextEdit()
        self.issues_text.setReadOnly(True)
        self.issues_text.setStyleSheet("background: #161b22;")
        is_layout.addWidget(self.issues_text)
        bottom_layout.addWidget(issues_group)

        splitter.addWidget(bottom)
        splitter.setSizes([240, 100])

        layout.addWidget(splitter, stretch=1)

        # Bottom button
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        self.btn_next = QPushButton("质控通过，进入补采建议 →")
        self.btn_next.setEnabled(False)
        self.btn_next.setProperty("cssClass", "nextButton")
        self.btn_next.clicked.connect(self._on_confirm)
        bottom_bar.addWidget(self.btn_next)
        layout.addLayout(bottom_bar)

    def _run_analysis(self):
        if not self._photo_paths:
            self.lbl_status.setText("无数据可供分析")
            return
        self.btn_run.setEnabled(False)
        self.progress.setVisible(True)
        self.lbl_status.setText("分析中...")
        self._worker = _QCWorker(self._photo_paths)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_analysis_done(self, report: QualityReport):
        self._report = report
        self.btn_run.setEnabled(True)
        self.progress.setVisible(False)

        # Update cards
        self.cards["pass"].setText(f"{report.pass_rate:.1f}%")
        c = "#27ae60" if report.pass_rate > 80 else "#f39c12" if report.pass_rate > 50 else "#e74c3c"
        self.cards["pass"].setStyleSheet(f"font-size: 22pt; font-weight: bold; color: {c};")

        self.cards["score"].setText(f"{report.overall_score:.0f}")
        c = "#27ae60" if report.overall_score > 70 else "#f39c12" if report.overall_score > 40 else "#e74c3c"
        self.cards["score"].setStyleSheet(f"font-size: 22pt; font-weight: bold; color: {c};")

        self.cards["blur"].setText(str(report.blur_issues))
        c = "#27ae60" if report.blur_issues == 0 else "#f39c12"
        self.cards["blur"].setStyleSheet(f"font-size: 22pt; font-weight: bold; color: {c};")

        self.cards["exposure"].setText(str(report.exposure_issues))
        c = "#27ae60" if report.exposure_issues == 0 else "#f39c12"
        self.cards["exposure"].setStyleSheet(f"font-size: 22pt; font-weight: bold; color: {c};")
        self.cards_frame.setVisible(True)

        # Populate table
        self.table.setRowCount(len(report.photos))
        for i, pq in enumerate(report.photos):
            self.table.setItem(i, 0, QTableWidgetItem(pq.path.name))
            self.table.setItem(i, 1, QTableWidgetItem(f"{pq.blur_score:.0f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{pq.exposure_mean:.0f}"))
            self.table.setItem(i, 3, QTableWidgetItem(
                "✓" if pq.resolution_ok else "✗"
            ))

            # Status column
            if not pq.issues:
                status = QTableWidgetItem("正常")
                status.setForeground(QColor("#27ae60"))
            else:
                status = QTableWidgetItem(", ".join(pq.issues))
                status.setForeground(QColor("#e74c3c"))
            self.table.setItem(i, 4, status)

        # Overlap info
        self.overlap_text.setText(
            f"估计重叠度: {report.overlap.estimated_overlap_pct:.0f}%\n"
            f"{report.overlap.note}"
        )
        if report.overlap.coverage_ok:
            self.overlap_text.setStyleSheet("font-size:11pt;padding:8px;color:#3fb950;")
        else:
            self.overlap_text.setStyleSheet("font-size:11pt;padding:8px;color:#f85149;")

        # Issues summary
        if report.blur_issues + report.exposure_issues + report.resolution_issues == 0:
            self.issues_text.setPlainText("未发现质量问题。")
        else:
            lines = []
            for pq in report.photos:
                if pq.issues:
                    lines.append(f"• {pq.path.name}: {', '.join(pq.issues)}")
            self.issues_text.setPlainText("\n".join(lines))

        self.lbl_status.setText(f"分析完成 — {report.summary.split(chr(10))[0]}")
        self.btn_next.setEnabled(True)

    def _on_error(self, msg: str):
        self.btn_run.setEnabled(True)
        self.progress.setVisible(False)
        self.lbl_status.setText(f"错误: {msg}")

    def _on_confirm(self):
        if self._report:
            self.data_ready.emit(self._report)
