"""模块5: 多尺度融合 - UI 页面."""
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

from oymm_app.modules.fusion import FusionEngine, FusionResult


class _FusionWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, score: float, mesh_vertices=None,
                 photo_poses=None, photo_paths=None):
        super().__init__()
        self.score = score
        self.mesh_vertices = mesh_vertices
        self.photo_poses = photo_poses
        self.photo_paths = photo_paths

    def run(self):
        try:
            result = FusionEngine.fuse(
                calibration_score=self.score,
                mesh_vertices=self.mesh_vertices,
                photo_poses=self.photo_poses,
                photo_paths=self.photo_paths,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class FusionPlot(FigureCanvasQTAgg):
    """3D colored point cloud showing fused result."""

    def __init__(self):
        self.fig = Figure(figsize=(7, 4), dpi=100)
        self.ax = self.fig.add_subplot(111, projection="3d")
        super().__init__(self.fig)

    def update_plot(self, result: FusionResult):
        self.ax.clear()
        # Subsample for display
        n_show = min(2000, result.point_count)
        idx = np.random.choice(result.point_count, n_show, replace=False)
        pts = result.points[idx]
        cols = result.colors[idx].astype(np.float32) / 255.0

        self.ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2],
                        c=cols, s=1, alpha=0.8)
        self.ax.set_xlabel("X (m)")
        self.ax.set_ylabel("Y (m)")
        self.ax.set_zlabel("Z (m)")
        self.ax.set_title(
            f"LiDAR + RGB 融合: {result.point_count:,} pts | "
            f"密度 {result.lidar_density:.0f} pts/m²",
            fontsize=9,
        )
        self.fig.tight_layout(pad=1)
        self.draw()


class FusionPage(QWidget):
    """Multi-scale fusion module page."""

    data_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._result: FusionResult | None = None
        self._setup_ui()

    def load_data(self, calibration_score: float = 100,
                   mesh_vertices=None, photo_poses=None, photo_paths=None):
        has_real = mesh_vertices is not None and len(mesh_vertices) > 0
        source = "真实网格+照片投影" if has_real else "模拟"
        self.lbl_status.setText(f"融合计算中 ({source})...")
        self.progress.setVisible(True)
        self.btn_run.setEnabled(False)

        self._worker = _FusionWorker(
            calibration_score, mesh_vertices, photo_poses, photo_paths)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel("多尺度融合")
        title.setProperty("cssClass", "titleLabel")
        layout.addWidget(title)

        desc = QLabel("LiDAR 骨架 + RGB 纹理融合，生成带真实色彩的三维点云模型。")
        desc.setProperty("cssClass", "subtitleLabel")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        toolbar = QHBoxLayout()
        self.btn_run = QPushButton("开始融合")
        self.btn_run.setProperty("cssClass", "runButton")
        self.btn_run.clicked.connect(lambda: self.load_data())
        toolbar.addWidget(self.btn_run)

        self.lbl_status = QLabel("点击开始融合")
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
            ("points", "点云总数"), ("density", "点密度"),
            ("coverage", "纹理覆盖率"), ("score", "融合评分"),
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

        # Main: 3D view + info
        splitter = QSplitter(Qt.Orientation.Horizontal)

        plot_group = QGroupBox("融合点云可视化 (左键旋转 | 右键/滚轮缩放 | 中键平移)")
        plot_layout = QVBoxLayout(plot_group)
        self.plot = FusionPlot()
        self.plot.setMinimumHeight(400)
        plot_layout.addWidget(self.plot)
        splitter.addWidget(plot_group)

        right = QWidget()
        right.setFixedWidth(200)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)

        info_group = QGroupBox("融合详情")
        info_layout = QVBoxLayout(info_group)
        self.info_text = QLabel("等待融合...")
        self.info_text.setWordWrap(True)
        self.info_text.setStyleSheet("font-size: 10pt; padding: 6px; background: #161b22;")
        self.info_text.setAlignment(Qt.AlignmentFlag.AlignTop)
        info_layout.addWidget(self.info_text)
        right_layout.addWidget(info_group)

        legend_group = QGroupBox("色彩说明")
        legend_layout = QVBoxLayout(legend_group)
        legend_text = QLabel(
            "地面: 绿/棕色\n"
            "植被: 深绿色\n"
            "建筑物: 灰/白色"
        )
        legend_text.setStyleSheet("font-size: 9pt; color: #8b949e; padding: 4px;")
        legend_layout.addWidget(legend_text)
        right_layout.addWidget(legend_group)

        splitter.addWidget(right)

        layout.addWidget(splitter, stretch=1)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self.btn_next = QPushButton("进入三维重建 →")
        self.btn_next.setEnabled(False)
        self.btn_next.setProperty("cssClass", "nextButton")
        self.btn_next.clicked.connect(self._on_confirm)
        bottom.addWidget(self.btn_next)
        layout.addLayout(bottom)

    def _on_done(self, result: FusionResult):
        self._result = result
        self.progress.setVisible(False)
        self.btn_run.setEnabled(True)
        self.cards_frame.setVisible(True)

        self.cards["points"].setText(f"{result.point_count:,}")
        self.cards["density"].setText(f"{result.lidar_density:.0f}")
        c = "#27ae60" if result.lidar_density > 15 else "#f39c12"
        self.cards["density"].setStyleSheet(f"font-size: 18pt; font-weight: bold; color: {c};")

        self.cards["coverage"].setText(f"{result.texture_coverage:.0%}")
        c = "#27ae60" if result.texture_coverage > 0.9 else "#f39c12"
        self.cards["coverage"].setStyleSheet(f"font-size: 18pt; font-weight: bold; color: {c};")

        sc = result.score
        c = "#27ae60" if sc > 80 else "#f39c12" if sc > 60 else "#e74c3c"
        self.cards["score"].setText(f"{sc:.0f}")
        self.cards["score"].setStyleSheet(f"font-size: 22pt; font-weight: bold; color: {c};")

        self.info_text.setText(
            f"总点数: {result.point_count:,}\n"
            f"点密度: {result.lidar_density:.1f} pts/m²\n"
            f"纹理覆盖率: {result.texture_coverage:.1%}\n"
            f"色彩一致性: {result.color_consistency:.1%}\n"
            f"\n融合评分: {result.score:.0f}/100\n"
            f"数据: {'真实网格投影' if '真实数据' in (result.summary or '') else '模拟数据'}"
        )
        self.plot.update_plot(result)
        self.lbl_status.setText(result.summary)
        self.btn_next.setEnabled(True)

    def _on_error(self, msg: str):
        self.btn_run.setEnabled(True)
        self.progress.setVisible(False)
        self.lbl_status.setText(f"错误: {msg}")

    def _on_confirm(self):
        if self._result:
            self.data_ready.emit(self._result)
