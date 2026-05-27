"""模块3: 动态补采建议 - UI 页面."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QSplitter, QTextEdit, QFrame, QProgressBar,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import numpy as np

from oymm_app.modules.resampling import (
    ResamplingAnalyzer, ResamplingReport, GapRegion,
)

SEVERITY_COLORS = {
    "critical": "#c0392b", "high": "#e74c3c",
    "medium": "#f39c12", "low": "#27ae60",
}


class CoverageHeatmap(FigureCanvasQTAgg):
    def __init__(self):
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)

    def update_map(self, report: ResamplingReport):
        self.ax.clear()
        cmap = self.ax.imshow(report.coverage.grid, cmap="RdYlGn",
                              vmin=0, vmax=1, origin="upper", interpolation="bilinear")
        self.fig.colorbar(cmap, ax=self.ax, label="Coverage", shrink=0.82)
        gap_mask = report.coverage.gap_mask
        size = gap_mask.shape[0]
        for y in range(size):
            for x in range(size):
                if gap_mask[y, x]:
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = y + dy, x + dx
                        if not (0 <= ny < size and 0 <= nx < size and gap_mask[ny, nx]):
                            self.ax.plot(x, y, "rx", markersize=0.5)
        self.ax.set_title(
            f"Coverage: {report.coverage.coverage_pct:.0f}% | "
            f"Gaps: {report.coverage.gap_pct:.1f}%", fontsize=10)
        self.ax.axis("off")
        self.fig.tight_layout(pad=0.5)
        self.draw()


class ResamplingPage(QWidget):
    data_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._report: ResamplingReport | None = None
        self._setup_ui()

    def load_from_qc(self, photo_count: int, overlap_pct: float,
                     width: int = 1920, height: int = 1080):
        self.lbl_status.setText("分析覆盖度...")
        self.progress.setVisible(True)
        self.btn_analyze.setEnabled(False)
        self._report = ResamplingAnalyzer.analyze(photo_count, overlap_pct, width, height)
        self._display_report()

    def load_poses(self, photo_poses: list[dict]):
        """Re-analyze coverage using real AT photo positions."""
        self.lbl_status.setText("基于真实位姿重新分析覆盖度...")
        self.progress.setVisible(True)
        self.btn_analyze.setEnabled(False)
        self._report = ResamplingAnalyzer.analyze_from_poses(photo_poses)
        self._display_report()
        self.summary_text.setPlainText(
            self._report.summary + f"\n(基于 {len(photo_poses)} 张照片的真实空三位姿)"
        )

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel("动态补采建议")
        title.setProperty("cssClass", "titleLabel")
        layout.addWidget(title)

        desc = QLabel("基于覆盖度分析，自动识别需补拍区域并生成建议航线。")
        desc.setProperty("cssClass", "subtitleLabel")
        layout.addWidget(desc)

        toolbar = QHBoxLayout()
        self.btn_analyze = QPushButton("重新分析")
        self.btn_analyze.setProperty("cssClass", "runButton")
        self.btn_analyze.clicked.connect(self._reanalyze)
        toolbar.addWidget(self.btn_analyze)

        self.lbl_status = QLabel("等待数据...")
        self.lbl_status.setProperty("cssClass", "statusLabel")
        toolbar.addWidget(self.lbl_status)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMaximum(0)
        layout.addWidget(self.progress)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        self.cards = {}
        for key, label in [
            ("coverage", "总覆盖度"), ("gaps", "空洞数"),
            ("waypoints", "建议点位"), ("severity", "最高严重度"),
        ]:
            card = QFrame()
            card.setStyleSheet("QFrame{background:#161b22;border-radius:6px;padding:6px;border:1px solid #30363d;}")
            cl = QVBoxLayout(card)
            val = QLabel("--")
            val.setStyleSheet("font-size:15pt;font-weight:bold;color:#c9d1d9;")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nm = QLabel(label)
            nm.setStyleSheet("font-size:9pt;color:#8b949e;")
            nm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(val)
            cl.addWidget(nm)
            cards_layout.addWidget(card)
            self.cards[key] = val
        self.cards_frame = QWidget()
        self.cards_frame.setLayout(cards_layout)
        self.cards_frame.setVisible(False)
        layout.addWidget(self.cards_frame)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        map_group = QGroupBox("覆盖度热力图")
        map_layout = QVBoxLayout(map_group)
        self.heatmap = CoverageHeatmap()
        map_layout.addWidget(self.heatmap)
        splitter.addWidget(map_group)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        gap_group = QGroupBox("空洞区域")
        gap_layout = QVBoxLayout(gap_group)
        self.gap_table = QTableWidget()
        self.gap_table.setColumnCount(4)
        self.gap_table.setHorizontalHeaderLabels(["ID", "位置", "面积%", "严重度"])
        self.gap_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.gap_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.gap_table.setAlternatingRowColors(True)
        gap_layout.addWidget(self.gap_table)
        right_layout.addWidget(gap_group)

        wp_group = QGroupBox("建议航线点位")
        wp_layout = QVBoxLayout(wp_group)
        self.wp_table = QTableWidget()
        self.wp_table.setColumnCount(5)
        self.wp_table.setHorizontalHeaderLabels(["X", "Y", "高度(m)", "方向", "优先级"])
        self.wp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.wp_table.setAlternatingRowColors(True)
        wp_layout.addWidget(self.wp_table)
        right_layout.addWidget(wp_group)

        splitter.addWidget(right)
        splitter.setSizes([240, 180])
        layout.addWidget(splitter, stretch=1)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(70)
        layout.addWidget(self.summary_text)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self.btn_next = QPushButton("进入跨模态校准 →")
        self.btn_next.setEnabled(False)
        self.btn_next.setProperty("cssClass", "nextButton")
        self.btn_next.clicked.connect(self._on_confirm)
        bottom.addWidget(self.btn_next)
        layout.addLayout(bottom)

    def _display_report(self):
        r = self._report
        if r is None:
            return
        self.progress.setVisible(False)
        self.btn_analyze.setEnabled(True)
        self.cards_frame.setVisible(True)

        cov = r.coverage.coverage_pct
        c = "#3fb950" if cov > 90 else "#d29922" if cov > 70 else "#f85149"
        self.cards["coverage"].setText(f"{cov:.0f}%")
        self.cards["coverage"].setStyleSheet(f"font-size:15pt;font-weight:bold;color:{c};")

        ng = len(r.gaps)
        c = "#3fb950" if ng == 0 else "#d29922" if ng < 3 else "#f85149"
        self.cards["gaps"].setText(str(ng))
        self.cards["gaps"].setStyleSheet(f"font-size:15pt;font-weight:bold;color:{c};")

        nw = len(r.suggested_waypoints)
        c = "#3fb950" if nw == 0 else "#d29922"
        self.cards["waypoints"].setText(str(nw))
        self.cards["waypoints"].setStyleSheet(f"font-size:15pt;font-weight:bold;color:{c};")

        sevs = [g.severity for g in r.gaps]
        worst = "无" if not sevs else max(sevs, key=lambda s: {"critical":4,"high":3,"medium":2,"low":1}.get(s,0))
        sc = SEVERITY_COLORS.get(worst, "#3fb950")
        self.cards["severity"].setText(worst)
        self.cards["severity"].setStyleSheet(f"font-size:12pt;font-weight:bold;color:{sc};")

        self.gap_table.setRowCount(len(r.gaps))
        for i, gap in enumerate(r.gaps):
            self.gap_table.setItem(i, 0, QTableWidgetItem(str(gap.id)))
            self.gap_table.setItem(i, 1, QTableWidgetItem(f"({gap.x_center:.2f}, {gap.y_center:.2f})"))
            self.gap_table.setItem(i, 2, QTableWidgetItem(f"{gap.area_pct:.1f}"))
            sev_item = QTableWidgetItem(gap.severity)
            sev_item.setForeground(QColor(SEVERITY_COLORS.get(gap.severity, "#333")))
            self.gap_table.setItem(i, 3, sev_item)

        self.wp_table.setRowCount(len(r.suggested_waypoints))
        for i, wp in enumerate(r.suggested_waypoints):
            self.wp_table.setItem(i, 0, QTableWidgetItem(f"{wp.x:.3f}"))
            self.wp_table.setItem(i, 1, QTableWidgetItem(f"{wp.y:.3f}"))
            self.wp_table.setItem(i, 2, QTableWidgetItem(f"{wp.altitude:.0f}"))
            self.wp_table.setItem(i, 3, QTableWidgetItem(wp.direction))
            pri = QTableWidgetItem(wp.priority)
            pri.setForeground(QColor(SEVERITY_COLORS.get(wp.priority, "#333")))
            self.wp_table.setItem(i, 4, pri)

        self.heatmap.update_map(r)
        self.summary_text.setPlainText(r.summary)
        self.lbl_status.setText(r.summary)
        self.btn_next.setEnabled(True)

    def _reanalyze(self):
        self.progress.setVisible(True)
        self.btn_analyze.setEnabled(False)

    def _on_confirm(self):
        if self._report:
            self.data_ready.emit(self._report)
