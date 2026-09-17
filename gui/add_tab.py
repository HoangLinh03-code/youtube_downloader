"""
gui/add_tab.py
---------------
Tab đầu tiên: nơi người dùng dán URL, xem trước video (thumbnail, tiêu đề,
mô tả) và chọn độ phân giải muốn tải từ một DANH SÁCH (QListWidget có
checkbox), sắp xếp từ thấp -> cao, rồi bấm "Thêm vào hàng đợi tải".

Tab này chỉ lo phần "chọn cái gì để tải" — việc tải & theo dõi tiến độ nằm
hoàn toàn ở tab Hàng đợi (queue_tab.py), theo đúng yêu cầu tách riêng từng
tính năng thay vì gộp chung 1 màn hình.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTextEdit, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QAbstractItemView, QFrame,
    QSizePolicy,
)

from core import downloader as dl
from core import utils

PLACEHOLDER_TEXT = "Dán 1 hoặc nhiều URL video/playlist YouTube, mỗi dòng 1 URL..."


@dataclass
class QueuedVideo:
    """Gói VideoInfo (thuộc core, không phụ thuộc GUI) kèm 1 id nội bộ để
    GUI dùng làm khoá tra cứu, không cần sửa dataclass gốc trong core/."""
    id: str
    info: dl.VideoInfo


class AddTab(QWidget):
    urls_submitted = pyqtSignal(list)                # list[str]
    add_to_queue_requested = pyqtSignal(object, list)  # QueuedVideo, list[int]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.videos: dict[str, QueuedVideo] = {}
        self.current_id: str | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        # --- Khu nhập URL ---
        input_row = QHBoxLayout()
        self.url_box = QTextEdit()
        self.url_box.setPlaceholderText(PLACEHOLDER_TEXT)
        self.url_box.setFixedHeight(70)
        input_row.addWidget(self.url_box, stretch=1)

        self.add_btn = QPushButton("➕ Thêm vào danh sách")
        self.add_btn.setFixedWidth(170)
        self.add_btn.clicked.connect(self._on_add_clicked)
        input_row.addWidget(self.add_btn)
        root.addLayout(input_row)

        # --- Splitter: trái = danh sách video đã thêm, phải = preview ---
        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, stretch=1)

        self.video_list = QListWidget()
        self.video_list.setIconSize(QSize(96, 54))
        self.video_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.video_list.currentItemChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.video_list)

        self.preview_panel = self._build_preview_panel()
        splitter.addWidget(self.preview_panel)
        splitter.setSizes([300, 560])

    def _build_preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.NoFrame)
        layout = QVBoxLayout(panel)

        self.thumb_label = QLabel("Chọn 1 video ở danh sách bên trái để xem trước")
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setFixedHeight(200)
        self.thumb_label.setStyleSheet(
            "background-color: #202225; color: #888; border-radius: 8px;"
        )
        layout.addWidget(self.thumb_label)

        self.title_label = QLabel("")
        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        self.title_label.setFont(f)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #aaaaaa;")
        self.desc_label.setMaximumHeight(80)
        self.desc_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        layout.addWidget(self.desc_label)

        self.max_res_label = QLabel("")
        self.max_res_label.setStyleSheet("color: #7aa2f7; font-style: italic;")
        layout.addWidget(self.max_res_label)

        layout.addWidget(QLabel("Chọn độ phân giải (có thể chọn nhiều, xếp từ thấp -> cao):"))

        self.res_list = QListWidget()
        self.res_list.setMaximumHeight(160)
        layout.addWidget(self.res_list)

        self.add_queue_btn = QPushButton("⬇ Thêm vào hàng đợi tải")
        self.add_queue_btn.clicked.connect(self._on_add_to_queue_clicked)
        self.add_queue_btn.setEnabled(False)
        layout.addWidget(self.add_queue_btn)

        layout.addStretch(1)
        return panel

    # ------------------------------------------------------------- slots
    def _on_add_clicked(self):
        raw = self.url_box.toPlainText().strip()
        if not raw:
            return
        urls = [u.strip() for u in raw.splitlines() if u.strip()]
        if not urls:
            return
        self.url_box.clear()
        self.urls_submitted.emit(urls)

    def _on_selection_changed(self, current: QListWidgetItem, _previous):
        if current is None:
            return
        qv: QueuedVideo = current.data(Qt.UserRole)
        self._show_preview(qv)

    def _on_add_to_queue_clicked(self):
        if self.current_id is None:
            return
        qv = self.videos.get(self.current_id)
        if qv is None:
            return
        heights = [
            self.res_list.item(i).data(Qt.UserRole)
            for i in range(self.res_list.count())
            if self.res_list.item(i).checkState() == Qt.Checked
        ]
        if not heights:
            return
        self.add_to_queue_requested.emit(qv, heights)

    # ------------------------------------------------------------ public
    def add_video(self, qv: QueuedVideo):
        """Được MainWindow gọi khi 1 URL đã lấy xong thông tin preview."""
        self.videos[qv.id] = qv
        title = qv.info.title or qv.info.url
        if qv.info.is_playlist:
            title = f"📃 {title}  ({qv.info.playlist_count} video)"
        item = QListWidgetItem(title)
        item.setData(Qt.UserRole, qv)
        self.video_list.addItem(item)
        if self.video_list.count() == 1:
            self.video_list.setCurrentItem(item)

    def set_thumbnail_pixmap(self, thumb_url: str, pixmap: QPixmap):
        """Cập nhật icon trong danh sách + ảnh preview lớn nếu đang chọn video đó."""
        small = pixmap.scaled(96, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            qv: QueuedVideo = item.data(Qt.UserRole)
            if qv.info.thumbnail == thumb_url:
                item.setIcon(QIcon(small))
                if qv.id == self.current_id:
                    self._set_big_thumbnail(pixmap)

    def _set_big_thumbnail(self, pixmap: QPixmap):
        scaled = pixmap.scaled(
            self.thumb_label.width() or 480, 200,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.thumb_label.setPixmap(scaled)
        self.thumb_label.setText("")

    def _show_preview(self, qv: QueuedVideo):
        self.current_id = qv.id
        info = qv.info

        self.thumb_label.setPixmap(QPixmap())
        self.thumb_label.setText("Đang tải thumbnail..." if info.thumbnail else "(Không có thumbnail)")

        title = info.title or info.url
        if info.is_playlist:
            title = f"📃 {title}  ({info.playlist_count} video)"
        self.title_label.setText(title)

        desc = (info.description or "").strip().replace("\n", " ")
        if len(desc) > 300:
            desc = desc[:300] + "…"
        self.desc_label.setText(desc or "(Không có mô tả)")

        if info.max_height:
            self.max_res_label.setText(
                f"Độ phân giải cao nhất hiện có: {utils.height_label(info.max_height)}"
            )
        else:
            self.max_res_label.setText("Không xác định được danh sách độ phân giải.")

        self.res_list.clear()
        for h in info.available_heights:  # đã sắp xếp thấp -> cao từ core
            item = QListWidgetItem(utils.height_label(h))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if h == info.max_height else Qt.Unchecked)
            item.setData(Qt.UserRole, h)
            self.res_list.addItem(item)
        self.add_queue_btn.setEnabled(self.res_list.count() > 0)
