# TKtagger

A powerful image tagging tool built with PySide6, supporting WD14 Tagger and bulk tag management.

> **Note:** This project uses AI assistance for coding.

---

## Interface

![Main Interface](src/Screenshot_20260510_223039.png)

English (README.md), Tiếng Việt (src/README_VN.md)

---

## Features

- **Bulk tag editing** — Add, remove, replace, or sort tags across multiple images at once
- **WD14 Tagger** — Automatic tagging via local model or external API
- **Undo / Redo** — Up to 256 steps with a full operation history window (`Edit → Operation history` or `🕐 History`)
- **Tag search** — Filter and find tags across your image set quickly with JEI-style multi-token search
- **Quick tag interaction** — Click directly on a tag to delete or insert
- **Optimized image loading** — Reduced memory usage and faster display
- **Multi-language support** — Interface available in multiple languages (i18n)
- **Command-line argument** — Launch directly into a folder: `python main.py [path_folder]`
- **Dictionary system** — Organize tags into named groups with virtual tag expansion
- **Resort by groups** — Reorder tags in `.txt` files according to dictionary group order, with ~~`BREAK`~~ `NewLine` ~~separator support for Kohya training~~ for visual look extenal editor

---

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python3 main.py

# Open directly into a specific folder
python3 main.py /path/to/folder_app
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+A` | Select all images |
| `Ctrl+I` | Invert selection |
| `Ctrl+D` | Deselect all |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+E` / `F5` | Remove duplicate tags |
| `Ctrl+R` / `F6` | Sort tags operations|
| `Ctrl+T` / `F8` | Open WD14 Tagger |
| `Ctrl+Shift+D` / `F9` | Open Dataset Calculator |

---

## Project Structure

```
TKtagger/
│
├── main.py                         # Entry point
├── main_window.py                  # MainWindow (QMainWindow) — core UI
├── settings_manager.py             # Singleton settings via ConfigParser (settings.ini)
├── settings.ini                    # User settings file (auto-generated)
│
├── tag_panel.py                    # Panel bên phải: danh sách tags theo thư mục
├── image_grid.py                   # Grid hiển thị ảnh, selection management
├── file_ops.py                     # Load/save images & tags, build folder tree
├── history_manager.py              # Undo/Redo stack manager
├── history_window.py               # UI panel hiển thị Action History
├── dialogs.py                      # AboutDialog và các dialog nhỏ
├── i18n.py                         # Internationalization (tr(), set_language())
│
├── defualt_dictbook.json           # Dict mẫu đi kèm app
├── requirements.txt                # Dependencies
│
├── lang/                           # Ngôn ngữ
│   ├── en.json                     # English
│   └── vi.json                     # Tiếng Việt
│
├── libs/                           # Reusable UI components
│   └── draggable_list.py           # Draggable list widget với per-item delete
│
├── tools/                          # Công cụ xử lý dataset
│   ├── waifu_tagger_window.py      # WD14 Tagger — auto-tag ảnh bằng ONNX / API
│   ├── tagger_logic.py             # Logic chạy inference (local + API mode)
│   ├── calculator_dataset.py       # Dataset Calculator dialog
│   ├── dict_tags.py                # Dict Tags manager + VirtualTagEngine
│   ├── remove_duplicate_tags.py    # Xoá tag trùng trong .txt files
│   ├── replace_tags.py             # Replace tags dialog (bulk edit)
│   └── resort_tag_window_operation.py  # Resort + Sort tags (gộp từ 2 file cũ)
│
└── src/                            # Assets
    ├── Qt_logo_2016.svg
    └── Screenshot_*.png            # Preview images cho README
```

---

## Changelog (overview) 1.4.1

### ✨ Added: Tính năng phụ
Auto-load Dict: Thiết lập đường dẫn sổ thẻ cố định tại menu Dict. App sẽ tự động load ngay khi khởi động qua settings.ini, không còn phải chọn thủ công mỗi lần mở máy.

Edit Menu mở rộng: Bổ sung các phím tắt tiêu chuẩn (Ctrl+A, D, I) và tính năng Nuke Selection (xóa sạch tag của ảnh đang chọn) để dọn dẹp dữ liệu nhanh.

### 🛠 Changes: Cấu trúc UX
Reorganize Project: Quy hoạch lại toàn bộ mã nguồn. Các script lẻ được đưa vào thư mục /tools, gộp các logic sắp xếp tương đồng vào một file duy nhất để dễ quản lý.

Folder Workflow: Thay cơ chế lưu trữ session. Bạn có thể nhảy giữa nhiều folder mà không mất state (không bị hỏi save liên tục); lệnh Ctrl+S giờ đây sẽ ghi đè toàn bộ thay đổi của tất cả các folder đã mở trong session ra folder.

INI Settings: Chuyển từ QSettings (Registry) sang file settings.ini nằm ngay cạnh app. Tiện cho việc backup hoặc di chuyển thư mục app mà không mất cấu hình.

Chuẩn hóa WD14 Tagger: Redesign lại cửa sổ tagger (thêm scrollbar, chỉnh size). Toàn bộ hệ thống nút bấm được áp dụng bộ mã màu chuẩn (_BTN_PRIMARY, _BTN_BROWSE),

Refactor Core: Loại bỏ biến self.lang thừa, gộp logic Resort Tags ra khỏi file main để code "sạch" hơn. Đồng nhất tiền tố i18n sang ldl_.

### 🐛 Fixed: Xử lý các lỗi

Lịch sử (History): Đảo ngược thứ tự hiển thị để hành động mới nhất luôn nằm đúng vị trí. Quan trọng nhất: WD14 Tagger đã có History, lỗi không thể Undo sau khi auto-tag đã biến mất.

UI Filter: Sửa lỗi Hidden Group vẫn hiển thị trên TagPanel và ResortTag dù đã đánh dấu ẩn.

**Note:** Chú ý: các thông tin này điều được AI viết tổng hợp qua.

## Roadmap

1. ✅ Basic tagger UI
2. ✅ Integrated WD14
3. ✅ Multiple language support
4. ✅ System dictionary tags
5. ✅ Redesigned UI

sau khi đã hoàn thành Roadmap nhì các update về phía sau đã số sẽ không thay đổi nhiều, chuyện về bảo trì sửa lỗi