"""
gui/video_item.py
------------------
Widget hiển thị 1 video (hoặc 1 playlist) trong hàng đợi tải:
  - Thumbnail + tiêu đề + mô tả rút gọn
  - Checkbox chọn 1 hoặC NHIỀU độ phân giải, xếp từ thấp -> cao
  - Với mỗi độ phân giải đã bấm "Tải", hiển thị 1 dòng tiến độ riêng
    (progress bar, %, tốc độ, ETA, nút Hủy, nút Mở thư mục sau khi xong)
"""

from __future__ import annotations

import io
import threading
import time
import uuid

import customtkinter as ctk
from PIL import Image

from core import downloader as dl
from core import utils


class ProgressRow(ctk.CTkFrame):
    """1 dòng tiến độ ứng với 1 (video, độ phân giải) đang/đã tải."""

    def __init__(self, master, height_label: str, on_cancel):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(1, weight=1)

        self.label = ctk.CTkLabel(self, text=height_label, width=110, anchor="w")
        self.label.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.bar = ctk.CTkProgressBar(self, height=14)
        self.bar.set(0)
        self.bar.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        self.status = ctk.CTkLabel(self, text="Đang chờ...", width=230, anchor="w")
        self.status.grid(row=0, column=2, padx=(0, 8), sticky="w")

        self.cancel_btn = ctk.CTkButton(
            self, text="Hủy", width=60, fg_color="#8a3b3b",
            hover_color="#a94444", command=on_cancel,
        )
        self.cancel_btn.grid(row=0, column=3, padx=(0, 4))

        self.open_btn = ctk.CTkButton(
            self, text="Mở thư mục", width=100, command=None, state="disabled",
        )
        self.open_btn.grid(row=0, column=4)

    def set_progress(self, frac: float, text: str):
        self.bar.set(max(0.0, min(1.0, frac)))
        self.status.configure(text=text)

    def set_done(self, folder: str):
        self.bar.set(1.0)
        self.status.configure(text="✅ Hoàn tất")
        self.cancel_btn.configure(state="disabled")
        self.open_btn.configure(state="normal", command=lambda: utils.open_folder(folder))

    def set_error(self, msg: str):
        self.status.configure(text=f"❌ Lỗi: {msg}"[:60])
        self.cancel_btn.configure(state="disabled")

    def set_cancelled(self):
        self.status.configure(text="⛔ Đã hủy")
        self.cancel_btn.configure(state="disabled")


class VideoItem(ctk.CTkFrame):
    def __init__(self, master, app, info: dl.VideoInfo):
        super().__init__(master, corner_radius=12, fg_color=("gray90", "gray17"))
        self.app = app
        self.info = info
        self.item_id = uuid.uuid4().hex[:8]
        self.rows: dict[int, ProgressRow] = {}
        self.check_vars: dict[int, ctk.BooleanVar] = {}

        self.grid_columnconfigure(1, weight=1)

        # --- Thumbnail ---
        self.thumb_label = ctk.CTkLabel(self, text="", width=160, height=90)
        self.thumb_label.grid(row=0, column=0, rowspan=3, padx=12, pady=12)
        self._load_thumbnail_async()

        # --- Tiêu đề + mô tả ---
        title = info.title or info.url
        if info.is_playlist:
            title = f"📃 {title}  ({info.playlist_count} video)"
        title_lbl = ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w", justify="left", wraplength=560,
        )
        title_lbl.grid(row=0, column=1, columnspan=2, sticky="w", padx=(0, 12), pady=(12, 0))

        desc = (info.description or "").strip().replace("\n", " ")
        if len(desc) > 160:
            desc = desc[:160] + "…"
        desc_lbl = ctk.CTkLabel(
            self, text=desc or "(Không có mô tả)", anchor="w", justify="left",
            wraplength=560, text_color=("gray30", "gray70"),
        )
        desc_lbl.grid(row=1, column=1, columnspan=2, sticky="w", padx=(0, 12))

        max_h_note = ""
        if info.max_height:
            max_h_note = f"Độ phân giải cao nhất hiện có: {utils.height_label(info.max_height)}"
        else:
            max_h_note = "Không xác định được danh sách độ phân giải."
        ctk.CTkLabel(
            self, text=max_h_note, anchor="w", text_color=("gray40", "gray60"),
            font=ctk.CTkFont(size=11, slant="italic"),
        ).grid(row=2, column=1, columnspan=2, sticky="w", padx=(0, 12))

        # --- Chọn độ phân giải (checkbox nhiều lựa chọn, thấp -> cao) ---
        res_frame = ctk.CTkFrame(self, fg_color="transparent")
        res_frame.grid(row=3, column=0, columnspan=3, sticky="w", padx=12, pady=(6, 4))
        ctk.CTkLabel(res_frame, text="Chọn độ phân giải (có thể chọn nhiều):").pack(
            side="left", padx=(0, 8)
        )
        for h in info.available_heights:  # đã sắp xếp thấp -> cao
            var = ctk.BooleanVar(value=(h == info.max_height))
            self.check_vars[h] = var
            ctk.CTkCheckBox(res_frame, text=utils.height_label(h), variable=var, width=1).pack(
                side="left", padx=4
            )

        self.start_btn = ctk.CTkButton(
            self, text="⬇ Tải độ phân giải đã chọn", command=self.start_selected
        )
        self.start_btn.grid(row=4, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 10))

        # --- Khu vực các dòng tiến độ, thêm động khi bắt đầu tải ---
        self.rows_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.rows_frame.grid(row=5, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 12))
        self.rows_frame.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    def _load_thumbnail_async(self):
        if not self.info.thumbnail:
            return
        threading.Thread(target=self._load_thumbnail, daemon=True).start()

    def _load_thumbnail(self):
        try:
            import requests
            resp = requests.get(self.info.thumbnail, timeout=10)
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            img.thumbnail((160, 90))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.app.enqueue(lambda: self.thumb_label.configure(image=ctk_img, text=""))
            self._thumb_ref = ctk_img  # giữ tham chiếu tránh bị garbage-collect
        except Exception:
            pass

    # ------------------------------------------------------------------
    def start_selected(self):
        selected = [h for h, v in self.check_vars.items() if v.get()]
        if not selected:
            self.app.log("[!] Chưa chọn độ phân giải nào.")
            return
        for h in selected:
            if h in self.rows:
                continue  # đã tải / đang tải rồi
            row = ProgressRow(
                self.rows_frame, utils.height_label(h),
                on_cancel=lambda h=h: self.app.cancel_download(self.item_id, h),
            )
            row.grid(row=len(self.rows), column=0, sticky="ew", pady=2)
            self.rows[h] = row
            self.app.submit_download(self, h)

    def get_row(self, height: int) -> ProgressRow | None:
        return self.rows.get(height)
