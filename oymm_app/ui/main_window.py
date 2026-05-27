"""主窗口 — 编辑器布局：图标栏 + 3D视口 + 属性面板."""
import platform
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt

from oymm_app.ui.icon_tab_bar import IconTabBar
from oymm_app.ui.viewport_manager import ViewportManager
from oymm_app.ui.property_panel import PropertyPanel
from oymm_app.ui.module_import import DataImportPage
from oymm_app.ui.module_quality import QualityControlPage
from oymm_app.ui.module_resampling import ResamplingPage
from oymm_app.ui.module_calibration import CalibrationPage
from oymm_app.ui.module_fusion import FusionPage
from oymm_app.ui.module_reconstruction import ReconstructionPage
from oymm_app.ui.module_export import ExportPage
from oymm_app.ui.module_classify import ClassifyPage

MODULES = [
    ("数据导入", "RGB + LiDAR + 多光谱"),
    ("智能质控", "重叠度 / 利用率 / 缺失检测"),
    ("补采建议", "空洞标记 + 航线建议"),
    ("跨模态校准", "RGB-LiDAR 配准 + 辐射归一化"),
    ("多尺度融合", "LiDAR骨架 + RGB纹理"),
    ("三维重建", "影像密集匹配 + 纹理映射"),
    ("成果输出", "FBX / 3DTiles / LAS / DOM"),
    ("基础解译", "NDVI + 阈值分类"),
]


class MainWindow(QMainWindow):
    """编辑器风格主窗口：左侧图标栏 | 中央3D视口 | 右侧属性面板."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Geosight - 三维重建展示系统")
        self._import_result = None
        self._completed: set[int] = set()
        self._current_module: int = 0
        self._pages: list[QWidget] = []
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Left: Icon Tab Bar ──
        self.tab_bar = IconTabBar()
        layout.addWidget(self.tab_bar)

        # Vertical separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("QFrame{color: rgba(255,255,255,0.06);}")
        sep.setFixedWidth(1)
        layout.addWidget(sep)

        # ── Center: Splitter (Viewport | Property Panel) ──
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(
            "QSplitter::handle{background: rgba(255,255,255,0.06);}"
        )

        # Viewport
        self.viewport = ViewportManager()
        self.splitter.addWidget(self.viewport)

        # Property Panel
        self.panel = PropertyPanel()
        self.splitter.addWidget(self.panel)

        self.splitter.setStretchFactor(0, 3)  # viewport
        self.splitter.setStretchFactor(1, 1)  # panel
        self.splitter.setSizes([900, 350])

        layout.addWidget(self.splitter, stretch=1)

        # ── Status Bar ──
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            f"就绪  |  GPU: RTX 4060 Laptop 8GB  |  Python {platform.python_version()}"
        )

    def _connect_signals(self):
        # Icon tab bar
        self.tab_bar.module_selected.connect(self._on_module_selected)

        # Instantiate all module pages
        self.import_page = DataImportPage()
        self.qc_page = QualityControlPage()
        self.resampling_page = ResamplingPage()
        self.calibration_page = CalibrationPage()
        self.fusion_page = FusionPage()
        self.recon_page = ReconstructionPage()
        self.recon_page._viewport = self.viewport  # Share viewport for mesh display
        self.export_page = ExportPage()
        self.export_page._viewport = self.viewport
        self.classify_page = ClassifyPage()
        self.classify_page._viewport = self.viewport

        self._pages = [
            self.import_page, self.qc_page, self.resampling_page,
            self.calibration_page, self.fusion_page, self.recon_page,
            self.export_page, self.classify_page,
        ]

        # Register each module's widget in the property panel
        for i, page in enumerate(self._pages):
            name, _ = MODULES[i]
            self.panel.register_module(i, name, page)

        # Data-ready signal chain (preserved from old layout)
        self.import_page.data_ready.connect(self._on_data_imported)
        self.qc_page.data_ready.connect(self._on_qc_done)
        self.resampling_page.data_ready.connect(self._on_resampling_done)
        self.calibration_page.data_ready.connect(self._on_calibration_done)
        self.fusion_page.data_ready.connect(self._on_fusion_done)
        self.recon_page.data_ready.connect(self._on_recon_done)
        self.export_page.data_ready.connect(self._on_export_done)
        self.classify_page.data_ready.connect(self._on_classify_done)

        # Activate module 0
        self._switch_to_module(0)

    # ── Module Navigation ──

    def _on_module_selected(self, index: int):
        """用户点击图标栏，自由切换到任意模块."""
        self._switch_to_module(index)

    def _switch_to_module(self, index: int):
        """切换活动模块：更新图标、面板、视口."""
        if not (0 <= index < len(self._pages)):
            return

        self._current_module = index
        self.tab_bar.set_active(index)
        self.panel.switch_to(index)

        # Modules 0-4: hide viewport, full-width panel
        # Modules 5-7: show viewport + compact panel
        if index < 5:
            self.viewport.setVisible(False)
            self.panel.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX — fill full width
            self.splitter.setSizes([0, self.splitter.width()])
        else:
            self.panel.setMaximumWidth(450)
            self.viewport.setVisible(True)
            self.splitter.setSizes([700, 300])
            self.viewport.activate_module(index)

        name, desc = MODULES[index]
        self.status_bar.showMessage(
            f"当前模块: {name}  |  GPU: RTX 4060 Laptop 8GB  |  Python {platform.python_version()}"
        )

    def _check_dependency(self, module_id: int) -> bool:
        """检查前置模块是否已完成."""
        if module_id == 0:
            return True
        return (module_id - 1) in self._completed

    def _mark_completed(self, index: int):
        """标记模块完成，更新图标栏."""
        if index not in self._completed:
            self._completed.add(index)
            self.tab_bar.mark_completed(index)
            self.tab_bar.update_progress(len(self._completed))

    def _advance(self, next_index: int):
        """推进到下一模块."""
        if 0 <= next_index < len(self._pages):
            self._switch_to_module(next_index)
            # Auto-load data if available
            if next_index == 1 and hasattr(self, '_import_result') and self._import_result:
                pass  # Already loaded in _on_data_imported

    # ── Pipeline Signal Handlers ──

    def _on_data_imported(self, result):
        self._import_result = result
        self._mark_completed(0)
        self.status_bar.showMessage(f"数据导入完成 — {result.summary}")
        self.qc_page.load_photos([p.path for p in result.rgb])
        self._advance(1)

    def _on_qc_done(self, report):
        self._mark_completed(1)
        self.status_bar.showMessage(
            f"质控完成 — 通过率: {report.pass_rate:.1f}% | 评分: {report.overall_score:.0f}"
        )
        self.resampling_page.load_from_qc(
            photo_count=report.total_count,
            overlap_pct=report.overlap.estimated_overlap_pct,
        )
        self._advance(2)

    def _on_resampling_done(self, report):
        self._mark_completed(2)
        self.status_bar.showMessage(f"补采分析完成 — {report.summary}")
        self.calibration_page.load_data()
        self._advance(3)

    def _on_calibration_done(self, report):
        self._mark_completed(3)
        self.status_bar.showMessage(f"校准完成 — Score: {report.overall_score:.0f}")
        self.fusion_page.load_data(report.overall_score)
        self._advance(4)

    def _on_fusion_done(self, result):
        self._mark_completed(4)
        self.status_bar.showMessage(
            f"融合完成 — {result.point_count:,} 点 | 评分: {result.score:.0f}"
        )
        self.recon_page.load_data()
        self._advance(5)

    def _on_recon_done(self, result):
        self._mark_completed(5)
        self.status_bar.showMessage(f"重建完成 — {result.get('tiles', '?')} 个瓦片")
        # Feed real AT photo poses back to resampling module for re-analysis
        photo_poses = result.get("photo_poses", [])
        if photo_poses:
            self.resampling_page.load_poses(photo_poses)
        self.export_page.load_data()
        self._advance(6)

    def _on_export_done(self, result):
        self._mark_completed(6)
        self.status_bar.showMessage("成果输出完成")
        self.classify_page.load_data()
        self._advance(7)

    def _on_classify_done(self, result):
        self._mark_completed(7)
        self.status_bar.showMessage("全部流程完成")
