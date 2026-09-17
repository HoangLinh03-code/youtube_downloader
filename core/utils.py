"""core/utils.py — các hàm tiện ích nhỏ dùng chung cho GUI."""

from __future__ import annotations

import os
import platform
import subprocess


def open_folder(path: str) -> None:
    """Mở thư mục chứa video trong trình quản lý file mặc định của hệ điều
    hành (Explorer/Finder/Nautilus...)."""
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:
        # Không để lỗi mở thư mục làm crash cả ứng dụng.
        pass


def format_bytes(n: float) -> str:
    if not n or n <= 0:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def height_label(h: int) -> str:
    """Gắn nhãn thân thiện cho độ phân giải, vd 2160 -> '2160p (4K)'."""
    tags = {
        4320: "8K", 2160: "4K", 1440: "2K/QHD", 1080: "Full HD",
        720: "HD", 480: "SD",
    }
    tag = tags.get(h)
    return f"{h}p ({tag})" if tag else f"{h}p"
