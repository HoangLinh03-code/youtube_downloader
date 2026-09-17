"""gui/log_tab.py — Tab thứ tư: log kỹ thuật (debug) của toàn bộ ứng dụng."""

from __future__ import annotations

import time

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PyQt5.QtGui import QFont


class LogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(5000)  # tránh log phình to vô hạn
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)
        mono.setPointSize(10)
        self.log_box.setFont(mono)
        layout.addWidget(self.log_box)

    def append_log(self, msg: str):
        self.log_box.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {msg}")
