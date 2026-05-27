"""Geosight - 三维重建展示系统 主入口."""
import sys

from PyQt6.QtWidgets import QApplication

from oymm_app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Geosight")
    app.setOrganizationName("Geosight")

    # Load dark theme
    from pathlib import Path
    qss_path = Path(__file__).parent / "ui" / "theme.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    window = MainWindow()
    window.resize(1280, 800)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
