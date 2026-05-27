"""模块7: 成果输出 UI."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QCheckBox, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from oymm_app.modules.export_formats import ExportEngine, FORMATS


class ExportPage(QWidget):
    data_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def load_data(self):
        self._display_formats()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel("成果输出")
        title.setProperty("cssClass", "titleLabel")
        layout.addWidget(title)

        desc = QLabel("多格式导出：FBX、OBJ、3D Tiles、LAS、DOM/DSM。")
        desc.setProperty("cssClass", "subtitleLabel")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Compact status card
        self._status_card = QLabel("就绪")
        self._status_card.setStyleSheet(
            "font-size:13pt;font-weight:bold;color:#3bf0b0;"
            "background:rgba(255,255,255,0.03);border-radius:6px;padding:8px;"
            "border:0.5px solid rgba(255,255,255,0.08);"
        )
        self._status_card.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_card)

        # Compact format checkboxes
        self.fmt_group = QGroupBox("导出格式")
        self.fmt_layout = QVBoxLayout(self.fmt_group)
        self.fmt_layout.setSpacing(2)
        self.checkboxes = {}
        for f in FORMATS:
            cb = QCheckBox(f"{f.name} ({f.ext}) [{f.size_estimate}]")
            cb.setChecked(True)
            cb.setStyleSheet("color:#c9d1d9;padding:2px 0;font-size:9pt;")
            self.fmt_layout.addWidget(cb)
            self.checkboxes[f.name] = cb
        layout.addWidget(self.fmt_group)

        layout.addStretch()

        bottom = QHBoxLayout()
        bottom.addStretch()
        self.btn_export = QPushButton("执行导出")
        self.btn_export.setProperty("cssClass", "runButton")
        self.btn_export.clicked.connect(self._export)
        bottom.addWidget(self.btn_export)

        self.btn_next = QPushButton("进入基础解译 →")
        self.btn_next.setProperty("cssClass", "nextButton")
        self.btn_next.clicked.connect(self._on_confirm)
        bottom.addWidget(self.btn_next)
        layout.addLayout(bottom)

    def _display_formats(self):
        self._status_card.setText("就绪 — 6 种格式可选")

    def _export(self):
        names = [n for n, cb in self.checkboxes.items() if cb.isChecked()]
        if not names:
            QMessageBox.warning(self, "提示", "请至少选择一种导出格式")
            return
        r = ExportEngine.export(names)
        self._status_card.setText(f"已导出 — {r.total_size}")
        QMessageBox.information(self, "导出完成", r.summary)

    def _on_confirm(self):
        self.data_ready.emit({"done": True})
