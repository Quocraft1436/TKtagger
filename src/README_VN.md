# TKtagger

Công cụ gắn thẻ ảnh mạnh mẽ xây dựng trên PySide6, hỗ trợ WD14 Tagger và chỉnh sửa thẻ hàng loạt cho dataset huấn luyện AI.

> **Ghi chú:** Dự án này sử dụng AI hỗ trợ lập trình.

---

[English](../README.md) · Tiếng Việt (README_VN.md)

---

## Giao diện

![Giao diện chính](Screenshot_20260831_112158.png)

---

## Tính năng

- **Chỉnh sửa thẻ hàng loạt** — Thêm, xóa, thay thế hoặc sắp xếp thẻ trên nhiều ảnh cùng lúc
- **WD14 Tagger** — Tự động gắn thẻ qua model ONNX cục bộ hoặc API ngoài
- **Hoàn tác / Làm lại** — Lên đến 256 bước với bảng lịch sử thao tác đầy đủ (`Chỉnh sửa → Lịch sử thao tác` hoặc `🕐 Lịch sử`)
- **Tìm kiếm thẻ** — Lọc và tìm thẻ nhanh theo kiểu JEI multi-token search
- **Tương tác thẻ nhanh** — Click trực tiếp vào thẻ để xóa hoặc chèn
- **Tải ảnh tối ưu** — Giảm bộ nhớ sử dụng, hiển thị nhanh hơn
- **Đa ngôn ngữ** — Giao diện hỗ trợ nhiều ngôn ngữ (i18n)
- **Tham số dòng lệnh** — Mở thẳng vào thư mục: `python main.py [đường_dẫn]`
- **Hệ thống từ điển thẻ** — Tổ chức thẻ thành nhóm với virtual tag expansion
- **Sắp xếp theo nhóm** — Tái sắp xếp thẻ trong file `.txt` theo thứ tự nhóm từ điển, hỗ trợ dấu phân cách `NewLine` để dễ đọc trên editor ngoài

---

## Cài đặt

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Chạy chương trình

```bash
python3 main.py

# Mở thẳng vào thư mục cụ thể
python3 main.py /đường/dẫn/thư/mục
```

---

## Phím tắt

| Phím tắt | Chức năng |
|----------|-----------|
| `Ctrl+A` | Chọn tất cả ảnh |
| `Ctrl+I` | Đảo ngược vùng chọn |
| `Ctrl+D` | Bỏ chọn tất cả |
| `Ctrl+Z` | Hoàn tác |
| `Ctrl+Y` | Làm lại |
| `Ctrl+E` / `F5` | Xóa thẻ trùng |
| `Ctrl+R` / `F6` | Sắp xếp thẻ |
| `Ctrl+T` / `F8` | Mở WD14 Tagger |
| `Ctrl+Shift+D` / `F9` | Mở Dataset Calculator |

---

## Cấu trúc dự án

```
TKtagger/
│
├── main.py                              # Điểm khởi chạy
├── main_window.py                       # MainWindow (QMainWindow) — UI chính
├── settings_manager.py                  # Quản lý cài đặt toàn cục qua ConfigParser (settings.ini)
├── settings.ini                         # File cấu hình người dùng (tự tạo khi chạy)
│
├── tag_panel.py                         # Panel bên phải: danh sách thẻ theo thư mục
├── image_grid.py                        # Grid hiển thị ảnh, quản lý vùng chọn
├── file_ops.py                          # Load/save ảnh & thẻ, build cây thư mục
├── history_manager.py                   # Quản lý stack Hoàn tác/Làm lại
├── history_window.py                    # Panel UI hiển thị Lịch sử thao tác
├── dialogs.py                           # AboutDialog và các dialog phụ
├── i18n.py                              # Đa ngôn ngữ (tr(), set_language())
│
├── defualt_dictbook.json                # Từ điển mẫu đi kèm ứng dụng
├── requirements.txt                     # Thư viện Python cần thiết
│
├── lang/                                # File ngôn ngữ
│   ├── en.json                          # Tiếng Anh
│   └── vi.json                          # Tiếng Việt
│
├── libs/                                # UI component tái sử dụng
│   └── draggable_list.py                # Widget list kéo thả với nút xóa từng item
│
├── tools/                               # Công cụ xử lý dataset
│   ├── waifu_tagger_window.py           # WD14 Tagger — tự động gắn thẻ qua ONNX / API
│   ├── tagger_logic.py                  # Logic inference (chế độ local + API)
│   ├── calculator_dataset.py            # Dialog Dataset Calculator
│   ├── dict_tags.py                     # Quản lý từ điển thẻ + VirtualTagEngine
│   ├── remove_duplicate_tags.py         # Xóa thẻ trùng trong file .txt
│   ├── replace_tags.py                  # Dialog thay thế thẻ (chỉnh sửa hàng loạt)
│   └── resort_tag_window_operation.py   # Resort + Sort thẻ (gộp từ 2 file cũ)
│
└── src/                                 # Tài nguyên
    ├── Qt_logo_2016.svg
    └── Screenshot_*.png                 # Ảnh preview cho README
```

---

## Nhật ký thay đổi — v1.5.0

### Added
- Tool mới: Swap Underscore (`tools/underscore_swap.py`) — chuyển đổi qua lại
  giữa dấu gạch dưới "_" và khoảng trắng " " trong tag, hỗ trợ áp dụng toàn cục.
- Menubar > Settings: cửa sổ cài đặt mới (`settings_dialog.py`) cho phép:
  - Chọn ngôn ngữ giao diện (đa ngôn ngữ, load từ `lang/*.json`)
  - Chọn định dạng file tag khi load: .txt / .cap / phần mở rộng tùy chỉnh
  - Giới hạn số lượng tối đa History (spinbox `max_history`)
- Tùy chọn vị trí khi thêm tag hàng loạt: chèn ở đầu (start) hoặc cuối (end)
  danh sách tag (`add_tag_to_selected`).
- Nút Chọn tất cả / Đảo chọn / Bỏ chọn tất cả cho panel filter tag chính
  (tag_panel.py).
- Preset dictionary: lưu đường dẫn và cấu trúc group dictionary đã dùng
  gần nhất vào `preset_user.json` để tái sử dụng nhanh.
- Chức năng Import tag mới chưa có trong dictionary (`ImportNewTagsDialog`
  trong dict_tags.py).

### Changed
- Cải thiện hiệu suất render card ảnh: thay thế nhiều QLabel riêng lẻ cho
  từng tag bằng widget vẽ tùy chỉnh `TagRenderWidget` (dùng QPainter),
  tag hiển thị dạng nền bo góc/label và có thể click để sửa.
- Refactor toàn diện cấu trúc code (nhiều module main_window, image_grid,
  dict_tags, resort_tag_window_operation được viết lại).

### Fixed
- Sửa lỗi resort tag không đồng bộ trạng thái hiển thị: giao diện (card ảnh,
  panel tag) nay được refresh trước khi hộp thoại thông báo "hoàn tất"
  xuất hiện, tránh tình trạng thông báo xong nhưng UI chưa cập nhật.

### Known gaps (chưa hoàn thành so với TODO)
- Cửa sổ Resort Tag: search bar tại đây mới chỉ có nút "Bỏ chọn tất cả",
  còn thiếu nút "Chọn tất cả" / "Đảo chọn" như đã có ở panel tag chính.


> Nội dung changelog được tổng hợp với sự hỗ trợ của AI.

---

## Lộ trình phát triển

- ✅ Giao diện tagger cơ bản
- ✅ Tích hợp WD14
- ✅ Hỗ trợ đa ngôn ngữ
- ✅ Hệ thống từ điển thẻ
- ✅ Thiết kế lại UI

Lộ trình cốt lõi đã hoàn thành. Các bản cập nhật tiếp theo sẽ tập trung vào bảo trì và sửa lỗi thay vì thêm tính năng lớn.
