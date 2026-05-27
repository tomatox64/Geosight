"""模块适配器基类 — 统一模块在编辑器布局中的接口."""
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget


class ModuleAdapter(QObject):
    """每个模块页面实现此接口，提供面板控件和视口交互.

    信号链保持与旧布局兼容: data_ready 由 MainWindow 统一连接.
    """

    data_ready = pyqtSignal(object)
    module_id: int = -1
    name: str = ""
    icon: str = ""

    def create_panel(self) -> QWidget:
        """返回嵌入右侧属性面板的控件 (紧凑布局)."""
        raise NotImplementedError

    def on_activate(self, viewport: "ViewportManager") -> None:
        """模块被切换到前台时调用，用于构建/恢复 3D 场景."""
        pass

    def on_deactivate(self, viewport: "ViewportManager") -> None:
        """模块被切走时调用，用于清理/隐藏 3D 场景."""
        pass

    def has_3d_content(self) -> bool:
        """是否在视口中渲染 3D 内容."""
        return False

    def load_data(self, *args, **kwargs) -> None:
        """接收上游模块传入的数据，触发本模块分析."""
        pass

    def get_dependency_module_id(self) -> int:
        """返回依赖的前置模块 ID，-1 表示无依赖."""
        return self.module_id - 1 if self.module_id > 0 else -1
