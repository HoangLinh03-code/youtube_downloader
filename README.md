# YouTube Downloader GUI

Giao diện đồ họa (CustomTkinter) cho phần lõi tải video bằng `yt-dlp`.

## Tính năng

- Dán 1 hoặc nhiều URL (video/playlist), mỗi dòng 1 link, bấm **Thêm vào danh sách**.
- Mỗi video hiển thị **preview**: thumbnail, tiêu đề, mô tả rút gọn.
- Danh sách độ phân giải hiển thị là **những gì THỰC SỰ có sẵn** cho video đó
  (lấy trực tiếp từ yt-dlp), sắp xếp từ thấp → cao. Nếu video gốc chỉ có tối đa
  1080p thì sẽ không có tuỳ chọn 2K/4K — ứng dụng ghi rõ dòng
  *"Độ phân giải cao nhất hiện có: ..."* ngay dưới tiêu đề để bạn biết lý do.
- Có thể **tick chọn nhiều độ phân giải cùng lúc** cho cùng 1 video (vd vừa
  1080p vừa 480p) — mỗi độ phân giải tải song song, có thanh tiến độ riêng.
- Chọn thư mục lưu bằng nút **Chọn thư mục lưu**.
- Sau khi tải xong, mỗi dòng có nút **Mở thư mục** để mở ngay nơi lưu file.
- Mỗi dòng tải có nút **Hủy** riêng để dừng giữa chừng.
- Tab **Debug / Log** ở dưới cùng hiển thị log kỹ thuật chi tiết (bật thêm
  "Chế độ debug chi tiết" để xem log verbose đầy đủ của yt-dlp).
- Hỗ trợ tải playlist nguyên vẹn cùng 1 độ phân giải (đặt tên file có số thứ
  tự tập, tự bỏ qua các tập đã tải nếu chạy lại nhờ file `downloaded.txt`).

## Cài đặt

```bash
pip install -r requirements.txt
```

Cài thêm **ffmpeg** (bắt buộc để ghép luồng video+audio cho độ phân giải cao):

- Windows: `winget install ffmpeg`
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

(Tùy chọn) Cài **aria2** nếu muốn tải nhanh hơn, rồi tick ô "Dùng aria2c" trong
ứng dụng. Lưu ý: khi bật aria2c, nút **Hủy** có thể không dừng ngay lập tức vì
aria2c chạy như một tiến trình riêng — mặc định ứng dụng để TẮT aria2c để nút
Hủy hoạt động tức thì.

## Chạy ứng dụng

```bash
python main.py
```

## Cấu trúc thư mục

```
youtube_downloader_gui/
├── main.py                # điểm khởi chạy
├── requirements.txt
├── core/
│   ├── downloader.py       # toàn bộ logic yt-dlp (không phụ thuộc GUI)
│   └── utils.py             # mở thư mục, định dạng hiển thị
└── gui/
    ├── app.py                # cửa sổ chính, điều phối tải đa luồng
    └── video_item.py          # widget 1 video trong hàng đợi
```

## Ghi chú

- Với **playlist**, danh sách độ phân giải hiển thị lấy mẫu từ tập đầu tiên
  (các tập khác trong cùng playlist có thể có độ phân giải gốc khác nhau đôi
  chút; yt-dlp vẫn tự lùi xuống mức cao nhất có sẵn cho từng tập khi tải).
- Tên file luôn có hậu tố độ phân giải **thực tế đã tải** (`%(height)sp`),
  nên nếu yt-dlp phải lùi xuống mức thấp hơn bạn chọn, tên file sẽ phản ánh
  đúng sự thật.
