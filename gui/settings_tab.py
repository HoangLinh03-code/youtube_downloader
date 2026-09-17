"""
gui/settings_tab.py
---------------------
Tab thứ ba: các tuỳ chọn chung áp dụng cho mọi lượt tải — thư mục lưu, có
dùng aria2c hay không, chế độ log chi tiết, số lượt tải chạy song song.
"""

from __future__ import annotations

import os

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QCheckBox,
    QLabel, QSpinBox, QFileDialog, QGroupBox, QFormLayout,
)

from core import downloader as dl


class SettingsTab(QWidget):
    max_concurrent_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._output_dir = os.path.abspath("downloads")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        folder_box = QGroupBox("Thư mục lưu video")
        fb_layout = QHBoxLayout(folder_box)
        self.folder_edit = QLineEdit(self._output_dir)
        self.folder_edit.setReadOnly(True)
        browse_btn = QPushButton("📁 Chọn thư mục...")
        browse_btn.clicked.connect(self._choose_folder)
        fb_layout.addWidget(self.folder_edit, stretch=1)
        fb_layout.addWidget(browse_btn)
        layout.addWidget(folder_box)

        speed_box = QGroupBox("Tốc độ / độ ổn định")
        speed_layout = QFormLayout(speed_box)

        self.aria2_check = QCheckBox(
            "Dùng aria2c để tải đa luồng, nhanh hơn (nút Hủy có thể chậm hơn)"
        )
        self.aria2_check.setChecked(False)
        if not dl.has_aria2c():
            self.aria2_check.setEnabled(False)
            self.aria2_check.setText(self.aria2_check.text() + "  — chưa cài aria2c trên máy")
        speed_layout.addRow(self.aria2_check)

        self.verbose_check = QCheckBox("Chế độ debug chi tiết (log verbose ở tab Debug)")
        speed_layout.addRow(self.verbose_check)

        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 8)
        self.concurrent_spin.setValue(4)
        self.concurrent_spin.valueChanged.connect(self.max_concurrent_changed.emit)
        speed_layout.addRow("Số lượt tải chạy song song tối đa:", self.concurrent_spin)

        layout.addWidget(speed_box)

        ffmpeg_note = QLabel(
            "✅ Đã tìm thấy ffmpeg." if dl.has_ffmpeg() else
            "⚠ Chưa tìm thấy ffmpeg — video độ phân giải cao cần ghép audio/video, "
            "hãy cài đặt ffmpeg (Windows: winget install ffmpeg | macOS: brew install "
            "ffmpeg | Linux: sudo apt install ffmpeg)."
        )
        ffmpeg_note.setWordWrap(True)
        layout.addWidget(ffmpeg_note)

        layout.addStretch(1)

    def _choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu video", self._output_dir)
        if path:
            self._output_dir = path
            self.folder_edit.setText(path)

    # --------------------------------------------------------- properties
    @property
    def output_dir(self) -> str:
        return self._output_dir

    @property
    def use_aria2(self) -> bool:
        return self.aria2_check.isChecked()

    @property
    def verbose(self) -> bool:
        return self.verbose_check.isChecked()

    @property
    def max_concurrent(self) -> int:
        return self.concurrent_spin.value()
