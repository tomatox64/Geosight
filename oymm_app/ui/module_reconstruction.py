"""模块6: 三维重建 - UI 页面."""
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QGroupBox, QFrame, QTextEdit, QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from oymm_app.cc_bridge.engine import engine_bridge

# Known OBJ output paths to auto-detect
_KNOWN_OBJ_PATHS = [
    "E:/oymm/projects/aukerman_demo/Productions/OYMM_Production/Data/Model/Model.obj",
    "E:/oymm/projects/geosight_demo/Productions/OYMM_Production/Data/Model/Model.obj",
    "E:/oymm/projects/test_scene/Productions/Geosight_Production/Data/Model/Model.obj",
]


class _ReconWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, photos_dir: str, project_dir: str):
        super().__init__()
        self.photos_dir = photos_dir
        self.project_dir = project_dir

    def run(self):
        import shutil
        try:
            name = "geosight_demo"
            proj_path = Path(self.project_dir)
            if proj_path.exists():
                shutil.rmtree(str(proj_path), ignore_errors=True)

            self.progress.emit("创建工程...")
            result = engine_bridge.create_project(
                Path(self.photos_dir), Path(self.project_dir), name
            )
            if not result.get("ok"):
                self.error.emit(result.get("error", "创建工程失败"))
                return

            project_path = result["project_path"]
            photos = result.get("photos_added", 0)
            self.progress.emit(f"工程创建完成，{photos} 张照片")

            self.progress.emit("启动引擎...")
            if not engine_bridge.start_engine():
                self.error.emit("引擎启动失败")
                return

            self.progress.emit("空三计算中...")
            at_result = engine_bridge.run_aerotriangulation(Path(project_path))
            if not at_result.get("ok"):
                self.error.emit(at_result.get("error", "空三失败"))
                return
            self.progress.emit("空三完成")

            self.progress.emit("提取照片位姿...")
            poses_result = engine_bridge.get_photo_poses(Path(project_path))
            photo_poses = poses_result.get("poses", [])
            self.progress.emit(f"获取到 {len(photo_poses)} 个照片位姿")

            self.progress.emit("提取连接点...")
            tp_result = engine_bridge.get_tie_points(Path(project_path))
            tie_points = tp_result.get("points", [])
            self.progress.emit(f"获取到 {len(tie_points)} 个连接点")

            self.progress.emit("三维重建中...")
            recon_result = engine_bridge.run_reconstruction(Path(project_path))
            if not recon_result.get("ok"):
                self.error.emit(recon_result.get("error", "重建失败"))
                return
            tiles = recon_result.get("tiles", 0)
            self.progress.emit(f"重建完成，{tiles} 个瓦片")

            self.progress.emit("导出模型中...")
            prod_result = engine_bridge.run_production(
                Path(project_path), output_format="OBJ"
            )
            if not prod_result.get("ok"):
                self.error.emit(prod_result.get("error", "导出失败"))
                return
            output_dir = prod_result.get("output_dir", "")
            self.progress.emit(f"导出完成: {output_dir}")

            engine_bridge.stop_engine()

            model_dir = Path(output_dir) / "Data" / "Model"
            obj_path = model_dir / "Model.obj"
            actual_obj = str(obj_path) if obj_path.exists() else None

            self.finished.emit({
                "project_path": project_path,
                "output_dir": output_dir,
                "obj_path": actual_obj,
                "tiles": tiles,
                "photos": photos,
                "photo_poses": photo_poses,
                "tie_points": tie_points,
            })

        except Exception as e:
            self.error.emit(str(e))


class ReconstructionPage(QWidget):
    """3D reconstruction module page."""

    data_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._result: dict | None = None
        self._mesh = None
        self._setup_ui()

    def load_data(self):
        """Check for existing model before starting pipeline."""
        existing_obj = self._find_existing_obj()
        if existing_obj:
            reply = QMessageBox.question(
                self, "已有模型文件",
                f"检测到已有的重建模型:\n\n"
                f"{existing_obj}\n\n"
                f"是否直接加载已有模型？\n"
                f"「是」加载已有 → 不重新重建\n"
                f"「否」重新重建 → 清除已有数据并重新运行 CC 管线",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._load_mesh_from_file(existing_obj)
                return

        self._start_pipeline()

    def _find_existing_obj(self) -> str | None:
        for p in _KNOWN_OBJ_PATHS:
            if Path(p).exists():
                return p
        return None

    def _start_pipeline(self):
        photos_dir = "E:/oymm/data/photos/aukerman/images"
        project_dir = "E:/oymm/projects/aukerman_demo"

        self.lbl_status.setText("启动重建管线...")
        self.progress.setVisible(True)
        self.progress.setMaximum(0)
        self.btn_run.setEnabled(False)
        self.log_text.clear()

        self._worker = _ReconWorker(photos_dir, project_dir)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_import_clicked(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入三维模型", "E:/oymm",
            "3D Models (*.obj *.fbx *.ply *.stl *.glb *.gltf);;All Files (*.*)"
        )
        if path:
            self._load_mesh_from_file(path)

    def _load_mesh_from_file(self, path: str):
        """Load and display a 3D mesh from file."""
        try:
            import pyvista as pv
            mesh = pv.read(path)
            self._mesh = mesh
            self._display_mesh(mesh)
            self.cards_frame.setVisible(True)
            self.cards["photos"].setText("导入")
            self.cards["tiles"].setText("1")
            n_faces = mesh.n_faces if hasattr(mesh, "n_faces") else "?"
            n_verts = mesh.n_points if hasattr(mesh, "n_points") else "?"
            self.info_text.setText(
                f"来源: {path}\n"
                f"模型: {n_verts} 顶点, {n_faces} 面\n"
                f"模式: 直接导入"
            )
            self.lbl_status.setText(f"模型已加载 — {Path(path).name}")
            self.btn_next.setEnabled(True)
            self._result = {"photos": "导入", "tiles": 1, "format": "IMPORT"}
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"无法加载模型:\n{e}")
            self._load_demo_mesh()

    def _display_mesh(self, mesh):
        """Render mesh in central viewport with appropriate settings."""
        has_tex = 'MaterialNames' in mesh.array_names
        if hasattr(self, '_viewport') and self._viewport is not None:
            try:
                for mid in (5, 6, 7):
                    self._viewport.set_module_actors(mid, [])
                    if has_tex:
                        self._viewport.add_mesh(
                            mid, mesh, show_edges=False,
                            smooth_shading=True, pbr=True,
                            metallic=0.0, roughness=0.6,
                            specular=0.1, ambient=0.3,
                        )
                    else:
                        self._viewport.add_mesh(
                            mid, mesh, color="#e8dcc8",
                            show_edges=False, smooth_shading=True,
                            pbr=True, metallic=0.05, roughness=0.7,
                            specular=0.3, ambient=0.2,
                        )
                    edges = mesh.extract_all_edges()
                    self._viewport.add_actor(mid, self._viewport.plotter.add_mesh(
                        edges, color="#333333", opacity=0.15,
                        line_width=0.3, name="_wire",
                    ))
                self._viewport.plotter.reset_camera()
                self._viewport.plotter.render()
            except Exception:
                pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title = QLabel("三维重建")
        title.setProperty("cssClass", "titleLabel")
        layout.addWidget(title)

        desc = QLabel("影像密集匹配 + 纹理映射 → 三维网格模型")
        desc.setProperty("cssClass", "subtitleLabel")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self.btn_run = QPushButton("开始重建")
        self.btn_run.setProperty("cssClass", "runButton")
        self.btn_run.clicked.connect(self.load_data)
        toolbar.addWidget(self.btn_run)

        self.btn_import = QPushButton("导入模型")
        self.btn_import.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.05);color:#8b949e;"
            "border:1px solid rgba(255,255,255,0.1);border-radius:4px;"
            "padding:4px 10px;font-size:9pt;}"
            "QPushButton:hover{background:rgba(255,255,255,0.1);color:#c9d1d9;}"
        )
        self.btn_import.clicked.connect(self._on_import_clicked)
        toolbar.addWidget(self.btn_import)

        self.lbl_status = QLabel("点击开始重建或导入模型")
        self.lbl_status.setProperty("cssClass", "statusLabel")
        toolbar.addWidget(self.lbl_status)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(6)
        self.cards = {}
        for key, label in [("photos", "照片"), ("tiles", "瓦片")]:
            card = QFrame()
            card.setStyleSheet(
                "QFrame{background:#161b22;border-radius:6px;padding:6px;border:1px solid #30363d;}"
            )
            cl = QVBoxLayout(card)
            cl.setSpacing(2)
            val = QLabel("--")
            val.setStyleSheet("font-size:14pt;font-weight:bold;color:#c9d1d9;")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nm = QLabel(label)
            nm.setStyleSheet("font-size:8pt;color:#8b949e;")
            nm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(val)
            cl.addWidget(nm)
            cards_layout.addWidget(card)
            self.cards[key] = val
        self.cards_frame = QWidget()
        self.cards_frame.setLayout(cards_layout)
        self.cards_frame.setVisible(False)
        layout.addWidget(self.cards_frame)

        self.viewer = None

        log_group = QGroupBox("处理日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(6, 4, 6, 4)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setStyleSheet("font-size:8pt;font-family:Consolas,monospace;")
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)

        self.info_text = QLabel("等待重建...")
        self.info_text.setWordWrap(True)
        self.info_text.setStyleSheet("font-size:9pt;color:#8b949e;padding:4px;")
        layout.addWidget(self.info_text)

        layout.addStretch()

        bottom = QHBoxLayout()
        bottom.addStretch()
        self.btn_next = QPushButton("进入成果输出 →")
        self.btn_next.setEnabled(False)
        self.btn_next.setProperty("cssClass", "nextButton")
        self.btn_next.clicked.connect(self._on_confirm)
        bottom.addWidget(self.btn_next)
        layout.addLayout(bottom)

    def _on_progress(self, msg: str):
        self.log_text.append(msg)
        self.lbl_status.setText(msg)

    def _on_done(self, result: dict):
        self._result = result
        self.progress.setVisible(False)
        self.btn_run.setEnabled(True)
        self.cards_frame.setVisible(True)

        self.cards["photos"].setText(str(result.get("photos", "?")))
        self.cards["tiles"].setText(str(result.get("tiles", 0)))

        obj_path = result.get("obj_path")
        if obj_path and Path(obj_path).exists():
            self._load_mesh_from_file(obj_path)
            self.info_text.setText(
                f"输出目录: {result.get('output_dir', '')}\n"
                f"格式: OBJ (带纹理)\n"
                f"文件: Model.obj + Model.mtl"
            )
            self.lbl_status.setText(
                f"重建完成 — {result.get('photos', '?')} 张照片 → {result.get('tiles', '?')} 个瓦片"
            )
            self.btn_next.setEnabled(True)
        else:
            self._load_demo_mesh()

    def _setup_professional_view(self, mesh):
        import pyvista as pv
        self.viewer.clear()
        bounds = mesh.bounds
        center = [(bounds[0]+bounds[1])/2, (bounds[2]+bounds[3])/2, (bounds[4]+bounds[5])/2]
        scene_size = max(bounds[1]-bounds[0], bounds[3]-bounds[2])

        self.viewer.add_mesh(
            mesh, color="#e8dcc8", show_edges=False, smooth_shading=True,
            specular=0.3, specular_power=20, diffuse=0.8, ambient=0.2,
            pbr=True, metallic=0.05, roughness=0.7,
        )
        self.viewer.add_mesh(
            mesh, style="wireframe", color="#333333",
            line_width=0.3, opacity=0.15, label="wireframe",
        )
        z_min = bounds[4]
        ground = pv.Plane(
            center=(center[0], center[1], z_min),
            direction=(0, 0, 1), i_size=scene_size*1.5, j_size=scene_size*1.5,
        )
        self.viewer.add_mesh(
            ground, color="#3a3a3e", opacity=0.4,
            show_edges=False, pbr=True, roughness=0.95, metallic=0.1, label="ground",
        )
        self.viewer.show_grid(
            xtitle="X (m)", ytitle="Y (m)", ztitle="Z (m)",
            color="#8b949e555", font_size=8, grid="back",
            show_xlabels=True, show_ylabels=True, show_zlabels=False,
        )
        self.viewer.remove_all_lights()
        for pos, col, inten in [
            ((scene_size, scene_size, scene_size*2), "#ffeedd", 1.2),
            ((-scene_size, scene_size*0.5, scene_size), "#ddeeff", 0.6),
            ((0, -scene_size, scene_size*0.5), "#ffffff", 0.8),
            ((0, 0, scene_size*3), "#8b949e899", 0.4),
        ]:
            self.viewer.add_light(pv.Light(position=pos, color=col, intensity=inten))
        self.viewer.set_background("#1a1a2e", top="#2d2d44")
        if hasattr(self.viewer, "enable_anti_aliasing"):
            self.viewer.enable_anti_aliasing("ssaa", 2)
        self.viewer.camera_position = [
            (center[0]+scene_size*0.8, center[1]-scene_size*0.6, center[2]+scene_size*0.7),
            (center[0], center[1], bounds[4]+(bounds[5]-bounds[4])*0.3),
            (0, 0, 1),
        ]

    def _on_error(self, msg: str):
        self.progress.setVisible(False)
        self.btn_run.setEnabled(True)
        self.lbl_status.setText("CC 管线未就绪，使用演示模型")
        self.log_text.append(f"CC: {msg}")
        self._load_demo_mesh()

    def _load_demo_mesh(self):
        import pyvista as pv
        import numpy as np

        x = np.linspace(-10, 10, 80)
        y = np.linspace(-10, 10, 80)
        xx, yy = np.meshgrid(x, y)
        zz = (np.sin(xx * 0.8) * np.cos(yy * 0.6) * 2
              + np.sin(xx * 0.3 + yy * 0.3) * 1.5
              + np.random.default_rng(42).normal(0, 0.15, xx.shape))

        terrain = pv.StructuredGrid(xx, yy, zz)
        mesh = terrain.extract_surface()

        self._mesh = mesh
        self.cards_frame.setVisible(True)
        self.cards["photos"].setText("60")
        self.cards["tiles"].setText("1")
        self.info_text.setText(
            "模式: 演示 (合成地形)\n数据: 60 张合成照片\n"
            "说明: CC 引擎需要真实 EXIF 数据\n当前显示为演示用合成模型"
        )
        self.lbl_status.setText("演示模式 — 合成 3D 地形已加载")
        self.btn_next.setEnabled(True)
        self._result = {"photos": 60, "tiles": 1, "format": "DEMO"}

        if hasattr(self, '_viewport') and self._viewport is not None:
            try:
                for mid in (5, 6, 7):
                    self._viewport.set_module_actors(mid, [])
                    self._viewport.add_mesh(
                        mid, mesh, color="#e8dcc8",
                        show_edges=False, smooth_shading=True,
                        pbr=True, metallic=0.05, roughness=0.7,
                        specular=0.3, ambient=0.2,
                    )
                    edges = mesh.extract_all_edges()
                    self._viewport.add_actor(mid, self._viewport.plotter.add_mesh(
                        edges, color="#333333", opacity=0.15,
                        line_width=0.3, name="_wire",
                    ))
                self._viewport.plotter.reset_camera()
                self._viewport.plotter.render()
            except Exception:
                pass

    def _on_confirm(self):
        if self._result:
            self.data_ready.emit(self._result)
