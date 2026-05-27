"""垂直图标工具栏 — 替代原有 QListWidget 侧边栏."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QToolButton, QButtonGroup, QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal


MODULE_ICONS = [
    ("①", "数据导入"),   # ①
    ("②", "智能质控"),   # ②
    ("③", "补采建议"),   # ③
    ("④", "跨模态校准"), # ④
    ("⑤", "多尺度融合"), # ⑤
    ("⑥", "三维重建"),   # ⑥
    ("⑦", "成果输出"),   # ⑦
    ("⑧", "基础解译"),   # ⑧
]


def get_module_icons() -> list[tuple[str, str]]:
    return MODULE_ICONS


class IconTabBar(QWidget):
    """48px 宽垂直图标工具栏，可自由切换模块."""

    module_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(56)
        self.setObjectName("IconTabBar")
        self._buttons: list[QToolButton] = []
        self._completed: set[int] = set()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(2)

        logo = QLabel("GS")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #8bb4ff;"
            "padding: 8px 0; letter-spacing: 2px;"
        )
        layout.addWidget(logo)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.06); margin: 4px 8px;")
        layout.addWidget(sep)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        for i, (icon_char, label) in enumerate(MODULE_ICONS):
            btn = QToolButton()
            btn.setText(f"{icon_char}\n{label[:2]}")
            btn.setToolTip(label)
            btn.setCheckable(True)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setMinimumHeight(52)
            btn.setObjectName(f"tabBtn{i}")
            btn.setProperty("cssClass", "iconTab")
            btn.clicked.connect(lambda checked, idx=i: self._on_clicked(idx))
            self._btn_group.addButton(btn, i)
            self._buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        self._status_dot = QLabel()
        self._status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_dot.setStyleSheet("font-size: 8pt; color: #484f58; padding: 8px 0;")
        self._status_dot.setText("○")
        layout.addWidget(self._status_dot)

    def _on_clicked(self, index: int):
        self.module_selected.emit(index)

    def set_active(self, index: int):
        """高亮指定模块按钮."""
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)

    def mark_completed(self, index: int):
        """在按钮上标记完成."""
        if index not in self._completed:
            self._completed.add(index)
            if index < len(self._buttons):
                icon_char, label = MODULE_ICONS[index]
                self._buttons[index].setText(f"●\n{label[:2]}")
                self._buttons[index].setStyleSheet(
                    "color: #3bf0b0; font-size: 9pt; font-weight: bold;"
                )

    def update_progress(self, completed_count: int):
        """更新底部进度指示."""
        total = len(MODULE_ICONS)
        self._status_dot.setText(f"● {completed_count}/{total}")
        if completed_count == total:
            self._status_dot.setStyleSheet("font-size: 8pt; color: #3bf0b0; padding: 8px 0;")
        elif completed_count > 0:
            self._status_dot.setStyleSheet("font-size: 8pt; color: #8bb4ff; padding: 8px 0;")
