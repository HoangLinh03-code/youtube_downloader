"""
gui/app.py
----------
MainWindow: chỉ đóng vai trò "nhạc trưởng" — nối tín hiệu giữa 4 tab
(Thêm video / Hàng đợi tải / Cài đặt / Debug) và các worker chạy nền
(QThreadPool). Bản thân từng tab không biết gì về nhau, toàn bộ điều phối
nằm ở đây, giúp mỗi tab độc lập, dễ bảo trì.
"""

from __future__ import annotations

import threading
import uuid

from PyQt5.QtCore import QThreadPool
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QTabWidget

from core import downloader as dl
from gui.add_tab import AddTab, QueuedVideo
from gui.log_tab import LogTab
from gui.queue_tab import QueueTab
from gui.settings_tab import SettingsTab
from gui.workers import WorkerSignals, FetchInfoWorker, ThumbnailWorker, DownloadWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Downloader")
        self.resize(1080, 720)

        self.pool = QThreadPool.globalInstance()
        self.signals = WorkerSignals()

        self.pending_requests: dict[str, str] = {}       # request_id -> url
        self.cancel_events: dict[tuple, threading.Event] = {}  # (task_id, height)

        self._build_ui()
        self._connect_signals()

        self.pool.setMaxThreadCount(self.settings_tab.max_concurrent)

        if not dl.has_ffmpeg():
            self.log_tab.append_log(
                "[CẢNH BÁO] Không tìm thấy ffmpeg — video độ phân giải cao cần ghép "
                "luồng video+audio, thiếu ffmpeg sẽ lỗi hoặc ra 2 file rời. Xem tab "
                "Cài đặt để biết cách cài."
            )

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        self.add_tab = AddTab()
        self.queue_tab = QueueTab()
        self.settings_tab = SettingsTab()
        self.log_tab = LogTab()

        tabs = QTabWidget()
        tabs.addTab(self.add_tab, "➕  Thêm video")
        tabs.addTab(self.queue_tab, "⬇  Hàng đợi tải")
        tabs.addTab(self.settings_tab, "⚙  Cài đặt")
        tabs.addTab(self.log_tab, "🐞  Debug / Log")
        self.tabs = tabs
        self.setCentralWidget(tabs)

    def _connect_signals(self):
        # Tab Thêm video -> điều phối
        self.add_tab.urls_submitted.connect(self.fetch_urls)
        self.add_tab.add_to_queue_requested.connect(self.start_downloads)

        # Tab Hàng đợi -> điều phối
        self.queue_tab.cancel_requested.connect(self.cancel_download)

        # Tab Cài đặt -> điều phối
        self.settings_tab.max_concurrent_changed.connect(self.pool.setMaxThreadCount)

        # Worker signals -> các tab
        self.signals.info_ready.connect(self.on_info_ready)
        self.signals.info_error.connect(self.on_info_error)
        self.signals.thumbnail_ready.connect(self.on_thumbnail_ready)
        self.signals.progress.connect(self.queue_tab.update_progress)
        self.signals.finished.connect(self._on_download_finished)
        self.signals.error.connect(self.queue_tab.mark_error)
        self.signals.cancelled.connect(self.queue_tab.mark_cancelled)
        self.signals.log.connect(self.log_tab.append_log)

    # --------------------------------------------------------- fetch info
    def fetch_urls(self, urls: list[str]):
        for url in urls:
            request_id = uuid.uuid4().hex
            self.pending_requests[request_id] = url
            worker = FetchInfoWorker(request_id, url, self.signals)
            self.pool.start(worker)

    def on_info_ready(self, request_id: str, info: dl.VideoInfo):
        self.pending_requests.pop(request_id, None)
        qv = QueuedVideo(id=uuid.uuid4().hex, info=info)
        self.add_tab.add_video(qv)
        self.log_tab.append_log(f"[+] Đã lấy thông tin: {info.title}")
        if info.thumbnail:
            self.pool.start(ThumbnailWorker(info.thumbnail, self.signals))

    def on_info_error(self, request_id: str, url: str, message: str):
        self.pending_requests.pop(request_id, None)
        self.log_tab.append_log(f"[LỖI] Không lấy được thông tin cho {url}: {message}")

    def on_thumbnail_ready(self, thumb_url: str, data: bytes):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self.add_tab.set_thumbnail_pixmap(thumb_url, pixmap)

    # ------------------------------------------------------------- tải xuống
    def start_downloads(self, qv: QueuedVideo, heights: list[int]):
        output_dir = self.settings_tab.output_dir
        for h in heights:
            key = (qv.id, h)
            if key in self.cancel_events:
                continue  # đã tải/đang tải độ phân giải này rồi
            self.queue_tab.add_task(qv.id, h, qv.info.title or qv.info.url, output_dir)

            cancel_event = threading.Event()
            self.cancel_events[key] = cancel_event

            worker = DownloadWorker(
                task_id=qv.id,
                url=qv.info.url,
                output_dir=output_dir,
                height=h,
                is_playlist=qv.info.is_playlist,
                cancel_event=cancel_event,
                signals=self.signals,
                use_aria2=self.settings_tab.use_aria2,
                verbose=self.settings_tab.verbose,
            )
            self.pool.start(worker)
        self.tabs.setCurrentWidget(self.queue_tab)

    def cancel_download(self, task_id: str, height: int):
        ev = self.cancel_events.get((task_id, height))
        if ev:
            ev.set()
            self.log_tab.append_log(f"[i] Đã gửi yêu cầu hủy tải ({height}p).")

    def _on_download_finished(self, task_id: str, height: int, output_dir: str):
        self.queue_tab.mark_finished(task_id, height)
        self.log_tab.append_log(f"[✓] Hoàn tất tải ở {height}p -> {output_dir}")
