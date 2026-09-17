"""
gui/workers.py
--------------
Các tác vụ chạy nền (QRunnable + QThreadPool) cho ứng dụng PyQt5:
  - FetchInfoWorker: lấy thông tin preview cho 1 URL
  - ThumbnailWorker: tải ảnh thumbnail (bytes) cho 1 URL ảnh
  - DownloadWorker: tải 1 video ở 1 độ phân giải cụ thể, báo tiến độ

QRunnable không tự có signal, nên mỗi worker giữ 1 instance WorkerSignals
(kế thừa QObject) để phát tín hiệu — đây là cách chuẩn khi dùng QThreadPool
trong PyQt5. Mọi signal đều được emit an toàn qua cơ chế Qt (tự động chuyển
sang thread chính khi slot được nối bằng Qt.AutoConnection mặc định).
"""

from __future__ import annotations

import threading

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal

from core import downloader as dl
from core import utils


class WorkerSignals(QObject):
    # Fetch thông tin video/playlist
    info_ready = pyqtSignal(str, object)      # (request_id, VideoInfo)
    info_error = pyqtSignal(str, str, str)    # (request_id, url, error_message)

    # Thumbnail
    thumbnail_ready = pyqtSignal(str, bytes)  # (url_thumbnail, raw_bytes)

    # Tải video: task_id định danh video, height là độ phân giải của dòng này
    progress = pyqtSignal(str, int, float, str)  # (task_id, height, fraction, text)
    finished = pyqtSignal(str, int, str)          # (task_id, height, output_dir)
    error = pyqtSignal(str, int, str)              # (task_id, height, message)
    cancelled = pyqtSignal(str, int)                # (task_id, height)

    log = pyqtSignal(str)


class FetchInfoWorker(QRunnable):
    """Lấy thông tin (preview) cho 1 URL, không tải file nào."""

    def __init__(self, request_id: str, url: str, signals: WorkerSignals):
        super().__init__()
        self.request_id = request_id
        self.url = url
        self.signals = signals

    def run(self):
        try:
            info = dl.fetch_info(self.url, log=self.signals.log.emit)
        except Exception as e:
            self.signals.info_error.emit(self.request_id, self.url, str(e))
            return
        self.signals.info_ready.emit(self.request_id, info)


class ThumbnailWorker(QRunnable):
    """Tải ảnh thumbnail về dạng bytes để tạo QPixmap ở thread chính."""

    def __init__(self, thumb_url: str, signals: WorkerSignals):
        super().__init__()
        self.thumb_url = thumb_url
        self.signals = signals

    def run(self):
        if not self.thumb_url:
            return
        try:
            import requests
            resp = requests.get(self.thumb_url, timeout=10)
            resp.raise_for_status()
            self.signals.thumbnail_ready.emit(self.thumb_url, resp.content)
        except Exception:
            pass  # thumbnail chỉ là phụ trợ, lỗi thì bỏ qua âm thầm


class DownloadWorker(QRunnable):
    """Tải 1 video (hoặc 1 playlist) ở 1 độ phân giải cụ thể."""

    def __init__(
        self,
        task_id: str,
        url: str,
        output_dir: str,
        height: int,
        is_playlist: bool,
        cancel_event: threading.Event,
        signals: WorkerSignals,
        use_aria2: bool = False,
        verbose: bool = False,
    ):
        super().__init__()
        self.task_id = task_id
        self.url = url
        self.output_dir = output_dir
        self.height = height
        self.is_playlist = is_playlist
        self.cancel_event = cancel_event
        self.signals = signals
        self.use_aria2 = use_aria2
        self.verbose = verbose

    def _on_progress(self, d: dict):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            frac = (downloaded / total) if total else 0.0
            speed = utils.format_bytes(d.get("speed") or 0) + "/s"
            eta = d.get("eta")
            eta_s = f"{eta}s" if eta else "?"
            text = f"{frac*100:.1f}%  •  {speed}  •  còn lại {eta_s}"
            self.signals.progress.emit(self.task_id, self.height, frac, text)
        elif status == "finished":
            self.signals.progress.emit(
                self.task_id, self.height, 1.0, "Đang ghép audio/video..."
            )

    def run(self):
        try:
            dl.download_item(
                url=self.url,
                output_dir=self.output_dir,
                target_height=self.height,
                is_playlist=self.is_playlist,
                cancel_event=self.cancel_event,
                on_progress=self._on_progress,
                on_log=self.signals.log.emit,
                use_aria2=self.use_aria2,
                verbose=self.verbose,
            )
        except dl.DownloadCancelled:
            self.signals.cancelled.emit(self.task_id, self.height)
        except Exception as e:
            self.signals.error.emit(self.task_id, self.height, str(e))
        else:
            self.signals.finished.emit(self.task_id, self.height, self.output_dir)
