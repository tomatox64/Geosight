"""视口管理器 — 持久化 pyvista 3D 视口，整个应用生命周期单例."""
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout

try:
    import pyvista as pv
    from pyvistaqt import QtInteractor
    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False


class ViewportManager(QWidget):
    """管理持久化 3D 视口和各模块的场景 actor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewportManager")
        self._module_actors: dict[int, list] = {}
        self._current_module: int = -1
        self._persistent_actors: list = []
        self._plotter = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if not HAS_PYVISTA:
            placeholder = QWidget()
            layout.addWidget(placeholder)
            return

        self._plotter = QtInteractor(self)
        self._plotter.set_background("#1a1a2e", top="#2d2d44")
        layout.addWidget(self._plotter.interactor)

        self._setup_persistent_scene()

    def _setup_persistent_scene(self):
        """添加始终可见的元素：坐标轴、地面参考面、灯光."""
        if not HAS_PYVISTA or self._plotter is None:
            return

        # Ground plane
        ground = pv.Plane(
            center=(0, 0, -2), direction=(0, 0, 1),
            i_size=30, j_size=30, i_resolution=2, j_resolution=2,
        )
        self._plotter.add_mesh(
            ground, color="#3a3a3e", opacity=0.15,
            show_edges=False, lighting=True, roughness=0.95,
            metallic=0.0, name="_ground",
        )

        # Axes
        self._plotter.show_axes()
        self._plotter.show_grid(
            xtitle="X", ytitle="Y", ztitle="Z",
            font_size=8, color="#484f58",
        )

        # Camera
        self._plotter.camera_position = "iso"
        self._plotter.camera.zoom(1.2)

        # Professional 3-point lighting
        self._setup_lighting()

        # Welcome text
        self._plotter.add_text(
            "Geosight — 三维重建展示系统\n点击左侧模块开始",
            position="upper_left", font_size=12,
            color="#8b949e", name="_welcome",
        )

    def _setup_lighting(self):
        """3 点照明方案."""
        if self._plotter is None:
            return
        self._plotter.remove_all_lights()
        light_positions = [
            (5, 5, 8),    # Key light: warm white, upper-right
            (-8, 0, 4),   # Fill light: cool blue, left
            (0, -5, 6),   # Rim light: white, behind
            (0, 0, 10),   # Ambient: neutral, top
        ]
        light_colors = ["#ffeedd", "#ddeeff", "#ffffff", "#aaaaaa"]
        light_intensities = [1.2, 0.6, 0.8, 0.4]
        for pos, col, intensity in zip(light_positions, light_colors, light_intensities):
            light = pv.Light(position=pos, color=col, intensity=intensity)
            self._plotter.add_light(light)

    @property
    def plotter(self):
        """返回底层 pyvista Plotter (QtInteractor)."""
        return self._plotter

    @property
    def current_module(self) -> int:
        return self._current_module

    def activate_module(self, module_id: int):
        """切换到指定模块的 3D 场景."""
        if self._plotter is None:
            return

        # Hide previous module actors
        if self._current_module >= 0:
            self._hide_module_actors(self._current_module)

        self._current_module = module_id

        # Remove welcome text after first activation
        try:
            self._plotter.remove_actor("_welcome")
        except (KeyError, AttributeError):
            pass

        # Show current module actors
        if module_id in self._module_actors:
            for actor in self._module_actors[module_id]:
                try:
                    self._plotter.add_actor(actor)
                except (ValueError, RuntimeError):
                    pass

        self._plotter.render()

    def _hide_module_actors(self, module_id: int):
        """隐藏指定模块的所有 actor."""
        if module_id not in self._module_actors:
            return
        for actor in self._module_actors[module_id]:
            try:
                self._plotter.remove_actor(actor, reset_camera=False)
            except (KeyError, ValueError, RuntimeError):
                pass

    def set_module_actors(self, module_id: int, actors: list):
        """替换指定模块的全部场景内容."""
        # Remove old actors for this module
        if module_id in self._module_actors:
            for actor in self._module_actors[module_id]:
                try:
                    self._plotter.remove_actor(actor, reset_camera=False)
                except (KeyError, ValueError, RuntimeError):
                    pass

        self._module_actors[module_id] = actors

        # If this module is active, show them
        if module_id == self._current_module:
            for actor in actors:
                try:
                    self._plotter.add_actor(actor)
                except (ValueError, RuntimeError):
                    pass
            self._plotter.render()

    def add_actor(self, module_id: int, actor):
        """添加单个 actor 到指定模块的场景."""
        if module_id not in self._module_actors:
            self._module_actors[module_id] = []
        self._module_actors[module_id].append(actor)
        if module_id == self._current_module:
            try:
                self._plotter.add_actor(actor)
                self._plotter.render()
            except (ValueError, RuntimeError):
                pass

    def clear_module(self, module_id: int):
        """清除指定模块的所有场景内容."""
        self._hide_module_actors(module_id)
        self._module_actors.pop(module_id, None)
        if self._current_module == module_id:
            self._plotter.render()

    def reset_view(self):
        """重置摄像机视角."""
        if self._plotter is not None:
            self._plotter.reset_camera()

    def add_mesh(self, module_id: int, mesh, **kwargs):
        """便捷方法：添加网格."""
        if self._plotter is None:
            return
        actor = self._plotter.add_mesh(mesh, **kwargs)
        self.add_actor(module_id, actor)
        return actor

    def add_points(self, module_id: int, points, **kwargs):
        """便捷方法：添加点云."""
        if self._plotter is None or not HAS_PYVISTA:
            return
        pv_points = pv.PolyData(points)
        actor = self._plotter.add_points(pv_points, **kwargs)
        self.add_actor(module_id, actor)
        return actor

    def add_text(self, module_id: int, text: str, **kwargs):
        """便捷方法：添加文字标签."""
        if self._plotter is None:
            return
        actor = self._plotter.add_text(text, **kwargs)
        self.add_actor(module_id, actor)
        return actor

    def show_default_scene(self):
        """显示默认场景 (无模块激活时)."""
        for mid in list(self._module_actors.keys()):
            self._hide_module_actors(mid)
        self._current_module = -1
        try:
            self._plotter.add_text(
                "Geosight — 三维重建展示系统\n点击左侧模块开始",
                position="upper_left", font_size=12,
                color="#8b949e", name="_welcome",
            )
        except (RuntimeError, ValueError):
            pass
        self._plotter.render()
