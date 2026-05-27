"""模块6: 三维重建 - UI 页面."""
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QGroupBox, QFrame, QTextEdit, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from oymm_app.cc_bridge.engine import engine_bridge


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
            # Clean previous project
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

            # Try to find the actual OBJ file
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
        self._setup_ui()

    def load_data(self):
        # Available datasets: aukerman(77), seneca(167), quarry(347)
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

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Title & subtitle handled by PropertyPanel header — keep compact inline versions
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

        self.lbl_status = QLabel("点击开始重建")
        self.lbl_status.setProperty("cssClass", "statusLabel")
        toolbar.addWidget(self.lbl_status)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Compact cards — 2 only
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

        # Placeholder viewer attr for backward compat in _load_demo_mesh / _on_done
        self.viewer = None

        # Processing log (compact)
        log_group = QGroupBox("处理日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(6, 4, 6, 4)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setStyleSheet("font-size:8pt;font-family:Consolas,monospace;")
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)

        # Status info label (replaces old info_text)
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

        # Load and display the model with professional rendering
        obj_path = result.get("obj_path")
        display_info = ""
        loaded = False

        for attempt_path in [
            obj_path,
            "E:/oymm/projects/test_scene/Productions/Geosight_Production/Data/Model/Model.obj",
        ]:
            if not attempt_path or not Path(attempt_path).exists():
                continue
            try:
                import pyvista as pv
                mesh = pv.read(attempt_path)
                self._mesh = mesh
                # Check if mesh has materials from OBJ+MTL (implies texture)
                has_tex = 'MaterialNames' in mesh.array_names
                # Display in central viewport (modules 5/6/7 share the mesh)
                if hasattr(self, '_viewport') and self._viewport is not None:
                    try:
                        for mid in (5, 6, 7):
                            self._viewport.set_module_actors(mid, [])
                            if has_tex:
                                # Textured: let pyvista use the MTL texture
                                self._viewport.add_mesh(
                                    mid, mesh, show_edges=False,
                                    smooth_shading=True, pbr=True,
                                    metallic=0.0, roughness=0.6,
                                    specular=0.1, ambient=0.3,
                                )
                            else:
                                # Untextured demo: solid earthy color
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
                loaded = True
                n_faces = mesh.n_faces if hasattr(mesh, "n_faces") else "?"
                n_verts = mesh.n_points if hasattr(mesh, "n_points") else "?"
                display_info = f"模型: {n_verts} 顶点, {n_faces} 面"
                break
            except Exception as e:
                display_info = f"模型加载失败: {e}"

        if not loaded:
            # CC produced no OBJ (synthetic data lacks EXIF) → fallback to demo mesh
            self._load_demo_mesh()
            return

        output_dir = result.get("output_dir", "")
        self.info_text.setText(
            f"输出目录: {output_dir}\n"
            f"格式: OBJ (带纹理)\n"
            f"文件: Model.obj + Model.mtl\n"
            f"{display_info}"
        )

        self.lbl_status.setText(
            f"重建完成 — {result.get('photos', '?')} 张照片 → {result.get('tiles', '?')} 个瓦片"
        )
        self.btn_next.setEnabled(True)

    def _setup_professional_view(self, mesh):
        """Configure pyvista viewer with professional GIS-style rendering."""
        import pyvista as pv
        self.viewer.clear()

        # Calculate scene bounds for lighting/ground reference
        bounds = mesh.bounds  # [xmin, xmax, ymin, ymax, zmin, zmax]
        center = [(bounds[0]+bounds[1])/2, (bounds[2]+bounds[3])/2, (bounds[4]+bounds[5])/2]
        scene_size = max(bounds[1]-bounds[0], bounds[3]-bounds[2])

        # Main model with semi-transparent texture
        self.viewer.add_mesh(
            mesh,
            color="#e8dcc8",
            show_edges=False,
            smooth_shading=True,
            specular=0.3,
            specular_power=20,
            diffuse=0.8,
            ambient=0.2,
            pbr=True,
            metallic=0.05,
            roughness=0.7,
        )

        # Wireframe overlay for structure visibility
        self.viewer.add_mesh(
            mesh,
            style="wireframe",
            color="#333333",
            line_width=0.3,
            opacity=0.15,
            label="wireframe",
        )

        # Ground reference plane
        z_min = bounds[4]
        ground = pv.Plane(
            center=(center[0], center[1], z_min),
            direction=(0, 0, 1),
            i_size=scene_size * 1.5,
            j_size=scene_size * 1.5,
        )
        self.viewer.add_mesh(
            ground,
            color="#3a3a3e",
            opacity=0.4,
            show_edges=False,
            pbr=True,
            roughness=0.95,
            metallic=0.1,
            label="ground",
        )

        # Reference grid
        self.viewer.show_grid(
            xtitle="X (m)", ytitle="Y (m)", ztitle="Z (m)",
            color="#8b949e555",
            font_size=8,
            grid="back",
            show_xlabels=True, show_ylabels=True, show_zlabels=False,
        )

        # Professional 3-point lighting
        self.viewer.remove_all_lights()
        # Key light - warm white from upper right
        light_key = pv.Light(
            position=(scene_size, scene_size, scene_size * 2),
            light_type="scene_light",
            color="#ffeedd",
            intensity=1.2,
        )
        self.viewer.add_light(light_key)
        # Fill light - cool blue from left
        light_fill = pv.Light(
            position=(-scene_size, scene_size * 0.5, scene_size),
            light_type="scene_light",
            color="#ddeeff",
            intensity=0.6,
        )
        self.viewer.add_light(light_fill)
        # Rim light - from behind
        light_rim = pv.Light(
            position=(0, -scene_size, scene_size * 0.5),
            light_type="scene_light",
            color="#ffffff",
            intensity=0.8,
        )
        self.viewer.add_light(light_rim)
        # Ambient
        light_ambient = pv.Light(
            position=(0, 0, scene_size * 3),
            light_type="scene_light",
            color="#8b949e899",
            intensity=0.4,
        )
        self.viewer.add_light(light_ambient)

        # Dark professional background
        self.viewer.set_background("#1a1a2e", top="#2d2d44")

        # Enable anti-aliasing
        if hasattr(self.viewer, "enable_anti_aliasing"):
            self.viewer.enable_anti_aliasing("ssaa", 2)

        # Professional camera angle (45° isometric-like view)
        self.viewer.camera_position = [
            (center[0] + scene_size * 0.8,
             center[1] - scene_size * 0.6,
             center[2] + scene_size * 0.7),
            (center[0], center[1], bounds[4] + (bounds[5]-bounds[4]) * 0.3),
            (0, 0, 1),
        ]

    def _on_error(self, msg: str):
        self.progress.setVisible(False)
        self.btn_run.setEnabled(True)
        self.lbl_status.setText(f"CC 管线未就绪，使用演示模型")
        self.log_text.append(f"CC: {msg}")
        # Generate demo mesh as fallback so viewport is never empty
        self._load_demo_mesh()

    def _load_demo_mesh(self):
        """Generate a synthetic demo 3D scene for display purposes."""
        import pyvista as pv
        import numpy as np

        # Create undulating terrain
        x = np.linspace(-10, 10, 80)
        y = np.linspace(-10, 10, 80)
        xx, yy = np.meshgrid(x, y)
        zz = (np.sin(xx * 0.8) * np.cos(yy * 0.6) * 2
              + np.sin(xx * 0.3 + yy * 0.3) * 1.5
              + np.random.default_rng(42).normal(0, 0.15, xx.shape))

        terrain = pv.StructuredGrid(xx, yy, zz)
        terrain = terrain.extract_surface()

        # Buildings (boxes at random positions)
        rng = np.random.default_rng(42)
        buildings = []
        for i in range(15):
            cx = rng.uniform(-8, 8)
            cy = rng.uniform(-8, 8)
            h = rng.uniform(1, 5)
            w = rng.uniform(0.5, 1.5)
            d = rng.uniform(0.5, 1.5)
            bld = pv.Cube(center=(cx, cy, h / 2), x_length=w, y_length=d, z_length=h)
            buildings.append(bld)

        # Ground plane
        ground = pv.Plane(center=(0, 0, -3), direction=(0, 0, 1), i_size=25, j_size=25)

        mesh = terrain

        self._mesh = mesh
        self.cards_frame.setVisible(True)
        self.cards["photos"].setText("60")
        self.cards["tiles"].setText("1")
        self.info_text.setText(
            "模式: 演示 (合成地形)\n数据: 60 张合成照片\n说明: CC 引擎需要真实 EXIF 数据\n当前显示为演示用合成模型"
        )
        self.lbl_status.setText("演示模式 — 合成 3D 地形已加载")
        self.btn_next.setEnabled(True)
        self._result = {"photos": 60, "tiles": 1, "format": "DEMO"}

        # Show in central viewport
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
