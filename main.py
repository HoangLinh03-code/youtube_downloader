#!/usr/bin/env python3
"""
YouTube Downloader GUI (PyQt5)
================================
Chạy: python main.py

Yêu cầu:  pip install -r requirements.txt
Khuyến nghị cài thêm ffmpeg (bắt buộc để ghép video độ phân giải cao):
    Windows: winget install ffmpeg
    macOS:   brew install ffmpeg
    Linux:   sudo apt install ffmpeg
"""

import sys

try:
    from PyQt5.QtWidgets import QApplication
except ImportError as e:
    print(f"Thiếu thư viện: {e}\nChạy: pip install -r requirements.txt")
    sys.exit(1)

from gui.app import MainWindow

DARK_QSS = """
QWidget {
    background-color: #1e1f22;
    color: #e6e6e6;
    font-size: 13px;
}
QMainWindow, QTabWidget::pane {
    background-color: #1e1f22;
    border: none;
}
QTabWidget::pane {
    border-top: 1px solid #33353a;
}
QTabBar::tab {
    background: #26282c;
    color: #cfcfcf;
    padding: 8px 16px;
    border: 1px solid #33353a;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #2f81f7;
    color: #ffffff;
}
QPushButton {
    background-color: #2f81f7;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover { background-color: #4a94ff; }
QPushButton:disabled { background-color: #3a3c40; color: #7a7c80; }
QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QTableWidget, QSpinBox {
    background-color: #26282c;
    border: 1px solid #33353a;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #2f81f7;
}
QHeaderView::section {
    background-color: #26282c;
    color: #cfcfcf;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #33353a;
}
QProgressBar {
    background-color: #26282c;
    border: 1px solid #33353a;
    border-radius: 6px;
    text-align: center;
    color: #e6e6e6;
}
QProgressBar::chunk {
    background-color: #2f81f7;
    border-radius: 6px;
}
QGroupBox {
    border: 1px solid #33353a;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QCheckBox::indicator, QListWidget::indicator {
    width: 16px;
    height: 16px;
}
QScrollBar:vertical {
    background: #1e1f22;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #3a3c40;
    border-radius: 5px;
    min-height: 20px;
}
"""


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_QSS)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
