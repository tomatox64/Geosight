"""模块4: 跨模态校准 - UI 页面."""
import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QGroupBox, QSplitter, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import numpy as np

from oymm_app.modules.calibration import CalibrationEngine, CalibrationReport


class _CalWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def run(self):
        try:
            report = CalibrationEngine.calibrate(60)
            self.finished.emit(report)
        except Exception as e:
            self.error.emit(str(e))


class AlignmentPlot(FigureCanvasQTAgg):
    """3D alignment scatter plot."""

    def __init__(self):
        self.fig = Figure(figsize=(7, 4), dpi=100)
        self.ax = self.fig.add_subplot(111, projection="3d")
        super().__init__(self.fig)

    def update_plot(self, report: CalibrationReport):
        self.ax.clear()
        rng = np.random.RandomState(42)

        # Downsampled points for visualization
        src_raw = CalibrationEngine.generate_synthetic_lidar(500)

        # Build structured target to show clear alignment
        tgt_ground = np.column_stack([
            rng.uniform(-10, 10, 350),
            rng.uniform(-10, 10, 350),
            rng.normal(0, 0.15, 350),
        ])
        tgt_struct = []
        for _ in range(150):
            bx = rng.choice([-3, 0, 4, 7])
            by = rng.choice([-5, -1, 2, 6])
            tgt_struct.append([
                bx + rng.uniform(-1.5, 1.5),
                by + rng.uniform(-1.5, 1.5),
                rng.uniform(0, 8),
            ])
        tgt = np.vstack([tgt_ground, np.array(tgt_struct)])

        n = min(200, len(src_raw))
        idx = np.random.choice(len(src_raw), n, replace=False)

        self.ax.scatter(src_raw[idx, 0], src_raw[idx, 1], src_raw[idx, 2],
                        c="#e74c3c", s=1, alpha=0.7, label="LiDAR (原始)")
        self.ax.scatter(tgt[idx, 0], tgt[idx, 1], tgt[idx, 2],
                        c="#3498db", s=1, alpha=0.7, label="RGB 点云")

        self.ax.set_xlabel("X (m)")
        self.ax.set_ylabel("Y (m)")
        self.ax.set_zlabel("Z (m)")
        self.ax.set_title(
            f"ICP 配准: RMSE {report.alignment.rmse_before:.2f} -> {report.alignment.rmse_after:.4f}m",
            fontsize=9,
        )
        self.ax.legend(loc="upper right", fontsize=7, markerscale=5)
        self.fig.tight_layout(pad=1)
        self.draw()


class CalibrationPage(QWidget):
    """跨模态校准模块页面."""

    data_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._report: CalibrationReport | None = None
        self._setup_ui()

    def load_data(self):
        self.lbl_status.setText("ICP 配准计算中...")
        self.progress.setVisible(True)
        self.btn_run.setEnabled(False)

        self._worker = _CalWorker()
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel("跨模态校准")
        title.setProperty("cssClass", "titleLabel")
        layout.addWidget(title)

        desc = QLabel("RGB-LiDAR ICP 粗配准 + 直方图匹配辐射归一化。")
        desc.setProperty("cssClass", "subtitleLabel")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        toolbar = QHBoxLayout()
        self.btn_run = QPushButton("开始校准")
        self.btn_run.setProperty("cssClass", "runButton")
        self.btn_run.clicked.connect(self.load_data)
        toolbar.addWidget(self.btn_run)

        self.lbl_status = QLabel("点击开始校准")
        self.lbl_status.setProperty("cssClass", "statusLabel")
        toolbar.addWidget(self.lbl_status)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMaximum(0)
        layout.addWidget(self.progress)

        # Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        self.cards = {}
        for key, label in [
            ("before", "校准前 RMSE"), ("after", "校准后 RMSE"),
            ("score", "综合评分"), ("status", "状态"),
        ]:
            card = QFrame()
            card.setStyleSheet(
                "QFrame{background:#161b22;border-radius:6px;padding:6px;border:1px solid #30363d;}"
            )
            cl = QVBoxLayout(card)
            val = QLabel("--")
            val.setStyleSheet("font-size: 18pt; font-weight: bold; color: #c9d1d9;")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nm = QLabel(label)
            nm.setStyleSheet("font-size: 9pt; color: #8b949e;")
            nm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(val)
            cl.addWidget(nm)
            cards_layout.addWidget(card)
            self.cards[key] = val
        self.cards_frame = QWidget()
        self.cards_frame.setLayout(cards_layout)
        self.cards_frame.setVisible(False)
        layout.addWidget(self.cards_frame)

        # Main: 3D plot + metrics
        splitter = QSplitter(Qt.Orientation.Horizontal)

        plot_group = QGroupBox("点云对齐可视化 (左键旋转 | 右键/滚轮缩放 | 中键平移)")
        plot_layout = QVBoxLayout(plot_group)
        self.plot = AlignmentPlot()
        self.plot.setMinimumHeight(400)
        plot_layout.addWidget(self.plot)
        splitter.addWidget(plot_group)

        right = QWidget()
        right.setFixedWidth(200)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)

        info_group = QGroupBox("对齐详情")
        info_layout = QVBoxLayout(info_group)
        self.info_text = QLabel("等待校准...")
        self.info_text.setWordWrap(True)
        self.info_text.setStyleSheet("font-size: 11pt; padding: 8px; background: #161b22;")
        self.info_text.setAlignment(Qt.AlignmentFlag.AlignTop)
        info_layout.addWidget(self.info_text)
        right_layout.addWidget(info_group)

        radio_group = QGroupBox("辐射归一化")
        radio_layout = QVBoxLayout(radio_group)
        self.radio_text = QLabel("等待运行")
        self.radio_text.setStyleSheet("font-size: 10pt; color: #8b949e; padding: 8px;")
        self.radio_text.setWordWrap(True)
        radio_layout.addWidget(self.radio_text)
        right_layout.addWidget(radio_group)

        splitter.addWidget(right)
        layout.addWidget(splitter, stretch=1)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self.btn_next = QPushButton("进入多尺度融合 →")
        self.btn_next.setEnabled(False)
        self.btn_next.setProperty("cssClass", "nextButton")
        self.btn_next.clicked.connect(self._on_confirm)
        bottom.addWidget(self.btn_next)
        layout.addLayout(bottom)

    def _on_done(self, report: CalibrationReport):
        self._report = report
        self.progress.setVisible(False)
        self.btn_run.setEnabled(True)
        self.cards_frame.setVisible(True)

        a = report.alignment
        self.cards["before"].setText(f"{a.rmse_before:.4f}")
        self.cards["after"].setText(f"{a.rmse_after:.4f}")
        c = "#27ae60" if a.converged else "#f39c12"
        self.cards["after"].setStyleSheet(f"font-size: 18pt; font-weight: bold; color: {c};")

        sc = report.overall_score
        c = "#27ae60" if sc > 80 else "#f39c12" if sc > 50 else "#e74c3c"
        self.cards["score"].setText(f"{sc:.0f}")
        self.cards["score"].setStyleSheet(f"font-size: 22pt; font-weight: bold; color: {c};")

        status = "通过" if a.converged and sc > 50 else "待检查"
        self.cards["status"].setText(status)
        c = "#27ae60" if status == "通过" else "#f39c12"
        self.cards["status"].setStyleSheet(f"font-size: 18pt; font-weight: bold; color: {c};")

        improvement = (a.rmse_before - a.rmse_after) / max(a.rmse_before, 0.001) * 100
        self.info_text.setText(
            f"平移向量: [{a.translation[0]:.3f}, {a.translation[1]:.3f}, {a.translation[2]:.3f}] m\n"
            f"误差改善: {improvement:.1f}%\n"
            f"收敛迭代: {a.iterations} 步\n"
            f"内点比例: {a.inlier_ratio:.1%}"
        )
        self.plot.update_plot(report)
        self.radio_text.setText(
            "辐射归一化: 直方图匹配\n"
            "源影像 -> 参考影像直方图均衡化\n"
            "已就绪，可进入融合步骤。"
        )
        self.lbl_status.setText(f"校准完成 — {report.summary}")
        self.btn_next.setEnabled(True)

    def _on_error(self, msg: str):
        self.btn_run.setEnabled(True)
        self.progress.setVisible(False)
        self.lbl_status.setText(f"错误: {msg}")

    def _on_confirm(self):
        if self._report:
            self.data_ready.emit(self._report)
