"""
core/downloader.py
-------------------
Toàn bộ logic "lõi" liên quan tới yt-dlp: lấy thông tin video/playlist để
preview, xác định danh sách độ phân giải thực sự khả dụng, và tải video có
báo tiến độ + hỗ trợ hủy giữa chừng.

Module này KHÔNG biết gì về giao diện (Tkinter/CustomTkinter) — nó chỉ nhận
các hàm callback (on_progress, on_log) để báo cáo trạng thái ra ngoài, nên có
thể tái sử dụng ở bất kỳ giao diện nào khác (CLI, web, ...).
"""

from __future__ import annotations

import os
import shutil
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

import yt_dlp


class DownloadCancelled(Exception):
    """Được ném ra bên trong progress_hook khi người dùng bấm nút Hủy,
    để buộc yt-dlp dừng vòng lặp tải giữa chừng."""


@dataclass
class VideoInfo:
    url: str
    id: str = ""
    title: str = ""
    description: str = ""
    thumbnail: str = ""
    duration: Optional[int] = None
    is_playlist: bool = False
    playlist_count: int = 0
    # Danh sách độ phân giải (chiều cao, px) THỰC SỰ có sẵn cho video này,
    # sắp xếp tăng dần, vd [360, 480, 720, 1080]
    available_heights: list = field(default_factory=list)
    max_height: int = 0
    raw_info: dict = field(default_factory=dict)


def has_aria2c() -> bool:
    return shutil.which("aria2c") is not None


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def is_playlist_url(url: str) -> bool:
    return ("list=" in url) or ("/playlist" in url)


def _collect_heights(info: dict) -> list:
    """Duyệt qua danh sách format trả về từ yt-dlp và gom các chiều cao
    (độ phân giải) khác nhau đang có sẵn cho video (chỉ tính format có
    luồng video, bỏ qua các format chỉ có audio)."""
    heights = set()
    for f in info.get("formats", []) or []:
        h = f.get("height")
        if h and f.get("vcodec") not in (None, "none"):
            heights.add(int(h))
    return sorted(heights)


def fetch_info(url: str, log: Callable[[str], None] = lambda m: None) -> VideoInfo:
    """Lấy thông tin video/playlist mà KHÔNG tải file nào (dùng để hiển thị
    preview: tiêu đề, mô tả, thumbnail, và danh sách độ phân giải khả dụng)."""
    playlist = is_playlist_url(url)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": not playlist,
        # Với playlist: không cần duyệt hết từng tập chi tiết cho preview,
        # chỉ cần thông tin cơ bản -> nhanh hơn nhiều.
        "extract_flat": False,
    }
    log(f"[info] Đang lấy thông tin: {url}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if playlist and info.get("entries") is not None:
        entries = [e for e in info["entries"] if e]
        first = entries[0] if entries else {}
        heights = _collect_heights(first)
        return VideoInfo(
            url=url,
            id=info.get("id", "") or "",
            title=info.get("title") or "(Playlist không có tiêu đề)",
            description=info.get("description", "") or "",
            thumbnail=(first.get("thumbnail") or info.get("thumbnail") or ""),
            is_playlist=True,
            playlist_count=len(entries),
            available_heights=heights,
            max_height=max(heights) if heights else 0,
            raw_info=info,
        )

    heights = _collect_heights(info)
    return VideoInfo(
        url=url,
        id=info.get("id", "") or "",
        title=info.get("title", "") or "",
        description=info.get("description", "") or "",
        thumbnail=info.get("thumbnail", "") or "",
        duration=info.get("duration"),
        is_playlist=False,
        available_heights=heights,
        max_height=max(heights) if heights else 0,
        raw_info=info,
    )


def build_format_string(target_height: Optional[int]) -> str:
    """Sinh chuỗi 'format' cho yt-dlp. Nếu target_height=None -> lấy chất
    lượng tốt nhất có thể. Nếu có target_height, ưu tiên đúng độ phân giải đó,
    yt-dlp sẽ TỰ ĐỘNG lùi xuống mức cao nhất thực có nếu video không có đúng
    độ phân giải yêu cầu (vd chọn 4K nhưng video gốc max 1080p)."""
    if not target_height:
        return "bestvideo+bestaudio/best"
    return (
        f"bestvideo[height<={target_height}][ext=mp4]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={target_height}]+bestaudio/"
        f"best[height<={target_height}]"
    )


class _YdlLogger:
    """Chuyển toàn bộ log nội bộ của yt-dlp ra một callback duy nhất, để GUI
    có thể hiển thị ở tab Debug."""

    def __init__(self, on_log: Callable[[str], None]):
        self.on_log = on_log

    def debug(self, msg):
        # yt-dlp gửi cả log debug lẫn 1 số thông báo info qua debug() khi
        # verbose=True; các dòng bắt đầu bằng [debug] là log kỹ thuật thuần.
        self.on_log(msg)

    def info(self, msg):
        self.on_log(msg)

    def warning(self, msg):
        self.on_log(f"[CẢNH BÁO] {msg}")

    def error(self, msg):
        self.on_log(f"[LỖI] {msg}")


def download_item(
    url: str,
    output_dir: str,
    target_height: Optional[int],
    is_playlist: bool,
    cancel_event: threading.Event,
    on_progress: Callable[[dict], None],
    on_log: Callable[[str], None],
    playlist_items: Optional[str] = None,
    use_aria2: bool = False,
    verbose: bool = False,
):
    """Tải 1 video (ở 1 độ phân giải cụ thể) hoặc 1 playlist trọn vẹn.

    - on_progress(d): được gọi liên tục với dict tiến độ gốc từ yt-dlp
      (status, downloaded_bytes, total_bytes, speed, eta, filename, ...).
    - on_log(str): được gọi với các dòng log kỹ thuật (tab Debug).
    - cancel_event: threading.Event, set() để yêu cầu hủy tải giữa chừng.

    Ném DownloadCancelled nếu bị hủy giữa chừng bởi người dùng.
    """
    os.makedirs(output_dir, exist_ok=True)

    # %(height)s phản ánh ĐỘ PHÂN GIẢI THỰC TẾ của file đã tải (không phải
    # độ phân giải người dùng yêu cầu) -> tên file luôn trung thực, và tránh
    # bị ghi đè khi tải cùng lúc nhiều độ phân giải của cùng 1 video.
    if is_playlist:
        outtmpl = os.path.join(
            output_dir,
            "%(playlist_title).80s",
            "%(playlist_index)03d - %(title).100s [%(id)s] - %(height)sp.%(ext)s",
        )
    else:
        outtmpl = os.path.join(
            output_dir, "%(title).100s [%(id)s] - %(height)sp.%(ext)s"
        )

    def hook(d):
        if cancel_event.is_set():
            raise DownloadCancelled("Người dùng đã hủy tải")
        on_progress(d)

    ydl_opts = {
        "format": build_format_string(target_height),
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "playlist_items": playlist_items,
        "ignoreerrors": True,
        "download_archive": os.path.join(output_dir, "downloaded.txt"),
        "concurrent_fragment_downloads": 8,
        "continuedl": True,
        "retries": 50,
        "fragment_retries": 50,
        "retry_sleep_functions": {"http": lambda n: min(4 * n, 30)},
        "socket_timeout": 30,
        "progress_hooks": [hook],
        "noprogress": True,
        "quiet": not verbose,
        "no_warnings": not verbose,
        "verbose": verbose,
        "noplaylist": not is_playlist,
        "logger": _YdlLogger(on_log),
    }

    # aria2c tải nhanh hơn nhưng chạy như 1 tiến trình ngoài, khiến nút Hủy
    # có thể không dừng NGAY lập tức (phải đợi tới lần cập nhật tiến độ kế
    # tiếp). Vì vậy để mặc định TẮT, người dùng tự bật nếu ưu tiên tốc độ.
    if use_aria2 and has_aria2c():
        ydl_opts["external_downloader"] = "aria2c"
        ydl_opts["external_downloader_args"] = {
            "aria2c": ["-x", "16", "-s", "16", "-k", "1M", "--continue=true"]
        }
        on_log("[i] Dùng aria2c để tải đa luồng (nút Hủy có thể chậm hơn).")
    else:
        on_log("[i] Dùng downloader mặc định của yt-dlp (hỗ trợ Hủy tức thì).")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
