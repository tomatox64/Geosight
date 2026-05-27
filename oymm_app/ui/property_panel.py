"""属性面板 — 右侧模块控制面板容器，带统一工具栏."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal


def _wrap(w: QWidget) -> QScrollArea:
    s = QScrollArea()
    s.setWidgetResizable(True)
    s.setWidget(w)
    s.setFrameShape(QScrollArea.Shape.NoFrame)
    s.setObjectName("panelScroll")
    return s


class PropertyPanel(QWidget):
    """右侧属性面板.

    顶部: 模块标题 + 运行按钮 + 状态
    中间: 模块控制面板 (可滚动)
    底部: 下一步按钮
    """

    run_requested = pyqtSignal(int)   # module_id
    next_requested = pyqtSignal(int)  # module_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PropertyPanel")
        self.setMinimumWidth(280)
        self.setMaximumWidth(450)
        self._modules: dict[int, tuple[str, QWidget, QPushButton | None, QPushButton | None]] = {}
        self._current_id: int = -1
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ──
        hdr = QWidget()
        hdr.setObjectName("panelHeader")
        hdr.setFixedHeight(48)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 6, 12, 6)
        hl.setSpacing(8)
        self._title = QLabel("")
        self._title.setObjectName("panelTitle")
        hl.addWidget(self._title)
        hl.addStretch()
        self._step_label = QLabel("")
        self._step_label.setObjectName("panelSubtitle")
        hl.addWidget(self._step_label)
        layout.addWidget(hdr)

        # ── Toolbar: Run + Status ──
        toolbar = QWidget()
        toolbar.setObjectName("panelToolbar")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(12, 4, 12, 4)
        tl.setSpacing(8)
        self._btn_run = QPushButton("▶ 运行")
        self._btn_run.setProperty("cssClass", "runButton")
        self._btn_run.setVisible(False)
        self._btn_run.clicked.connect(self._on_run_clicked)
        tl.addWidget(self._btn_run)
        self._lbl_status = QLabel("")
        self._lbl_status.setProperty("cssClass", "statusLabel")
        self._lbl_status.setWordWrap(True)
        tl.addWidget(self._lbl_status, stretch=1)
        layout.addWidget(toolbar)

        # ── Content Stack ──
        self._stack = QStackedWidget()
        self._stack.setObjectName("panelStack")
        layout.addWidget(self._stack, stretch=1)

        # ── Bottom Action ──
        bottom = QWidget()
        bottom.setObjectName("panelBottom")
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(12, 6, 12, 6)
        bl.addStretch()
        self._btn_next = QPushButton("下一步 →")
        self._btn_next.setProperty("cssClass", "nextButton")
        self._btn_next.setVisible(False)
        self._btn_next.clicked.connect(self._on_next_clicked)
        bl.addWidget(self._btn_next)
        layout.addWidget(bottom)

    def register_module(self, module_id: int, name: str, panel: QWidget):
        """注册模块的控制面板.

        自动扫描面板中的 runButton 和 nextButton，
        将其隐藏（由面板统一工具栏接管）.
        """
        # Find and hide page-level title/subtitle to avoid duplication
        for child in panel.findChildren(QLabel):
            css = child.property("cssClass")
            if css in ("titleLabel", "subtitleLabel"):
                child.setVisible(False)
            # Shrink big card values for compact panel
            if css in ("accentValue", "successValue", "warningValue", "dangerValue"):
                child.setStyleSheet(child.styleSheet().replace("18pt", "14pt").replace("22pt", "16pt"))

        # Find run and next buttons, hide the page-level ones (panel toolbar replaces them)
        run_btn = panel.findChild(QPushButton, "runBtn") or self._find_by_css(panel, "runButton")
        next_btn = panel.findChild(QPushButton, "nextBtn") or self._find_by_css(panel, "nextButton")
        if run_btn:
            run_btn.setVisible(False)
        if next_btn:
            next_btn.setVisible(False)

        self._modules[module_id] = (name, panel, run_btn, next_btn)
        self._stack.insertWidget(module_id, _wrap(panel))

    @staticmethod
    def _find_by_css(widget: QWidget, css_class: str):
        for child in widget.findChildren(QPushButton):
            if child.property("cssClass") == css_class:
                return child
        for child in widget.findChildren(QLabel):
            if child.property("cssClass") == css_class:
                return child
        return None

    def switch_to(self, module_id: int):
        """切换到指定模块的面板."""
        if module_id not in self._modules:
            return

        self._current_id = module_id
        name, panel, run_btn, next_btn = self._modules[module_id]
        self._title.setText(name)
        self._step_label.setText(f"{module_id + 1}/8")
        self._stack.setCurrentIndex(module_id)

        # Show/hide run button based on whether page has one
        self._btn_run.setVisible(run_btn is not None)
        if run_btn is not None:
            self._btn_run.setText(run_btn.text())

        # Show/hide next button
        self._btn_next.setVisible(next_btn is not None)
        if next_btn is not None:
            self._btn_next.setText(next_btn.text())

    def set_status(self, text: str):
        """更新工具栏状态文字."""
        self._lbl_status.setText(text)

    def set_next_enabled(self, enabled: bool):
        self._btn_next.setEnabled(enabled)

    def _on_run_clicked(self):
        if self._current_id < 0:
            return
        _, _, run_btn, _ = self._modules.get(self._current_id, (None, None, None, None))
        if run_btn:
            run_btn.click()

    def _on_next_clicked(self):
        if self._current_id < 0:
            return
        _, _, _, next_btn = self._modules.get(self._current_id, (None, None, None, None))
        if next_btn:
            next_btn.click()
