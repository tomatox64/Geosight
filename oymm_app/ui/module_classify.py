"""模块8: 基础解译 UI."""
import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QFrame, QSplitter,
)
from PyQt6.QtCore import Qt, pyqtSignal

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import numpy as np

from oymm_app.modules.classification import Classifier, ClassificationResult


class NDVIChart(FigureCanvasQTAgg):
    def __init__(self):
        self.fig = Figure(figsize=(5, 3.5), dpi=100)
        self.fig.set_facecolor("#0a0a0f")
        self.ax_hist = self.fig.add_subplot(211)
        self.ax_pie = self.fig.add_subplot(212)
        super().__init__(self.fig)

    def update_chart(self, r: ClassificationResult):
        self.ax_hist.clear(); self.ax_pie.clear()
        for ax in [self.ax_hist, self.ax_pie]:
            ax.set_facecolor("#0a0a0f")

        # NDVI histogram
        rng = np.random.RandomState(77)
        ndvi = np.concatenate([
            rng.normal(0.65, 0.12, 35000), rng.normal(0.15, 0.08, 10000),
            rng.normal(0.25, 0.10, 20000), rng.normal(0.18, 0.06, 35000),
        ])
        self.ax_hist.hist(ndvi, bins=50, color="#3bf0b0", alpha=0.7, edgecolor="#1a4a3a")
        self.ax_hist.axvline(0.4, color="#f0c040", linestyle="--", label="植被阈值")
        self.ax_hist.set_title(f"NDVI 分布 (μ={r.ndvi_mean:.3f}, σ={r.ndvi_std:.3f})", color="#c9d1d9", fontsize=9)
        self.ax_hist.tick_params(colors="#8b949e", labelsize=7)
        self.ax_hist.legend(fontsize=7, facecolor="#0a0a0f", edgecolor="#30363d", labelcolor="#c9d1d9")

        # Pie
        labels = ["植被", "水体", "裸地", "建筑"]
        sizes = [r.vegetation_pct, r.water_pct, r.bareland_pct, r.building_pct]
        colors = ["#3bf0b0", "#58a6ff", "#f0c040", "#8b949e"]
        self.ax_pie.pie(sizes, labels=labels, colors=colors, autopct="%1.0f%%",
                        textprops={"color": "#c9d1d9", "fontsize": 8})
        self.ax_pie.set_title("地物分类占比", color="#c9d1d9", fontsize=9)

        self.fig.tight_layout(pad=2)
        self.draw()


class ClassifyPage(QWidget):
    data_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def load_data(self):
        self.lbl_status.setText("分析中...")
        self._result = Classifier.analyze()
        self._display()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title = QLabel("基础解译")
        title.setProperty("cssClass", "titleLabel")
        layout.addWidget(title)

        desc = QLabel("NDVI 植被指数 + 阈值分类")
        desc.setProperty("cssClass", "subtitleLabel")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        toolbar = QHBoxLayout()
        self.btn_run = QPushButton("开始分析")
        self.btn_run.setProperty("cssClass", "runButton")
        self.btn_run.clicked.connect(self.load_data)
        toolbar.addWidget(self.btn_run)
        self.lbl_status = QLabel("点击开始分析")
        self.lbl_status.setProperty("cssClass", "statusLabel")
        toolbar.addWidget(self.lbl_status)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 2x2 card grid for classification results
        cards_w = QWidget()
        cards_grid = QHBoxLayout(cards_w)
        cards_grid.setSpacing(4)
        self.cards = {}
        for col_keys in [("veg", "植被"), ("water", "水体"), ("bare", "裸地"), ("bld", "建筑")]:
            key, label = col_keys
            card = QFrame()
            card.setStyleSheet(
                "QFrame{background:rgba(255,255,255,0.03);border-radius:6px;"
                "padding:4px;border:0.5px solid rgba(255,255,255,0.08);}"
            )
            cl2 = QVBoxLayout(card)
            cl2.setSpacing(1)
            v = QLabel("--")
            v.setStyleSheet("font-size:12pt;font-weight:bold;color:#c9d1d9;")
            v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            n = QLabel(label)
            n.setStyleSheet("font-size:7pt;color:#8b949e;")
            n.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl2.addWidget(v); cl2.addWidget(n)
            cards_grid.addWidget(card)
            self.cards[key] = v
        self.cf = cards_w
        self.cf.setVisible(False)
        layout.addWidget(self.cf)

        # Compact legend (no chart — viewport handles 3D NDVI overlay)
        legend = QGroupBox("分类图例")
        ll = QVBoxLayout(legend)
        ll.setSpacing(2)
        for name, color in [("植被 (>0.4)", "#3bf0b0"), ("建筑 (0.3-0.4)", "#8b949e"),
                             ("裸地 (0.1-0.3)", "#f0c040"), ("水体 (<0.1)", "#58a6ff")]:
            row = QHBoxLayout()
            row.setSpacing(4)
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{color};font-size:11pt;")
            lbl = QLabel(name)
            lbl.setStyleSheet("color:#c9d1d9;font-size:8pt;")
            row.addWidget(dot); row.addWidget(lbl); row.addStretch()
            ll.addLayout(row)
        layout.addWidget(legend)

        # NDVI summary line
        self._ndvi_summary = QLabel("")
        self._ndvi_summary.setStyleSheet("font-size:8pt;color:#8b949e;padding:2px 0;")
        self._ndvi_summary.setWordWrap(True)
        layout.addWidget(self._ndvi_summary)

        layout.addStretch()
        self.btn_next = QPushButton("完成 →")
        self.btn_next.setProperty("cssClass", "nextButton")
        self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self._on_confirm)
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(self.btn_next)
        layout.addLayout(bottom)

    def _display(self):
        r = self._result
        self.cf.setVisible(True)
        self.cards["veg"].setText(f"{r.vegetation_pct}%")
        self.cards["veg"].setStyleSheet("font-size:12pt;font-weight:bold;color:#3bf0b0;")
        self.cards["water"].setText(f"{r.water_pct}%")
        self.cards["water"].setStyleSheet("font-size:12pt;font-weight:bold;color:#58a6ff;")
        self.cards["bare"].setText(f"{r.bareland_pct}%")
        self.cards["bare"].setStyleSheet("font-size:12pt;font-weight:bold;color:#f0c040;")
        self.cards["bld"].setText(f"{r.building_pct}%")
        self.cards["bld"].setStyleSheet("font-size:12pt;font-weight:bold;color:#8b949e;")
        self._ndvi_summary.setText(f"NDVI μ={r.ndvi_mean:.3f} σ={r.ndvi_std:.3f} | {r.summary}")
        self.lbl_status.setText(r.summary)
        self.btn_next.setEnabled(True)

    def _on_confirm(self):
        self.data_ready.emit({"done": True})
