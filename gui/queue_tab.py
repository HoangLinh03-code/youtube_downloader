"""
gui/queue_tab.py
------------------
Tab thứ hai: bảng tổng hợp TẤT CẢ các lượt tải đang/đã chạy — mỗi dòng ứng
với 1 cặp (video, độ phân giải). Tách hẳn khỏi tab Thêm video để màn hình
không bị gộp chung nhiều chức năng.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QProgressBar, QPushButton, QHeaderView, QLabel,
)

from core import utils

COL_VIDEO, COL_RES, COL_PROGRESS, COL_STATUS, COL_ACTIONS = range(5)


class QueueTab(QWidget):
    cancel_requested = pyqtSignal(str, int)  # (task_id, height)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: dict[tuple[str, int], dict] = {}  # (task_id, height) -> widgets
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Danh sách các lượt tải (mỗi độ phân giải là 1 dòng riêng):"))

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Video", "Độ phân giải", "Tiến độ", "Trạng thái", "Thao tác"]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_VIDEO, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_RES, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_PROGRESS, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_ACTIONS, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        layout.addWidget(self.table)

    # ------------------------------------------------------------ public
    def add_task(self, task_id: str, height: int, video_title: str, output_dir: str):
        key = (task_id, height)
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, COL_VIDEO, QTableWidgetItem(video_title))
        self.table.setItem(row, COL_RES, QTableWidgetItem(utils.height_label(height)))

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        self.table.setCellWidget(row, COL_PROGRESS, bar)

        status_item = QTableWidgetItem("Đang chờ...")
        self.table.setItem(row, COL_STATUS, status_item)

        actions = QWidget()
        h = QHBoxLayout(actions)
        h.setContentsMargins(2, 2, 2, 2)
        cancel_btn = QPushButton("Hủy")
        cancel_btn.setStyleSheet("background-color:#8a3b3b;")
        cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(task_id, height))
        open_btn = QPushButton("Mở thư mục")
        open_btn.setEnabled(False)
        open_btn.clicked.connect(lambda: utils.open_folder(output_dir))
        h.addWidget(cancel_btn)
        h.addWidget(open_btn)
        self.table.setCellWidget(row, COL_ACTIONS, actions)

        self.rows[key] = {
            "row": row, "bar": bar, "status": status_item,
            "cancel_btn": cancel_btn, "open_btn": open_btn,
        }

    def update_progress(self, task_id: str, height: int, frac: float, text: str):
        w = self.rows.get((task_id, height))
        if not w:
            return
        w["bar"].setValue(int(max(0.0, min(1.0, frac)) * 100))
        w["status"].setText(text)

    def mark_finished(self, task_id: str, height: int):
        w = self.rows.get((task_id, height))
        if not w:
            return
        w["bar"].setValue(100)
        w["status"].setText("✅ Hoàn tất")
        w["cancel_btn"].setEnabled(False)
        w["open_btn"].setEnabled(True)

    def mark_error(self, task_id: str, height: int, message: str):
        w = self.rows.get((task_id, height))
        if not w:
            return
        w["status"].setText(f"❌ Lỗi: {message}"[:80])
        w["cancel_btn"].setEnabled(False)

    def mark_cancelled(self, task_id: str, height: int):
        w = self.rows.get((task_id, height))
        if not w:
            return
        w["status"].setText("⛔ Đã hủy")
        w["cancel_btn"].setEnabled(False)
