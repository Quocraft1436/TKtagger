# Cấu trúc dự án TKtagger

[README English](README.md) · [README tiếng Việt](README_VI.md) · [Tutorial English](tutorial.md) · [Hướng dẫn tiếng Việt](tutorial_vi.md)

TKtagger là ứng dụng desktop Python/PySide6. Các widget giao diện chính nằm ở thư mục gốc, tiện ích dùng chung nằm trong `libs/`, còn cửa sổ và logic công cụ dataset nằm trong `tools/`.

## Sơ đồ thư mục

```text
TKtagger/
├── README.md                   # Giới thiệu bằng tiếng Anh
├── README_VI.md                 # Giới thiệu bằng tiếng Việt
├── tutorial.md                  # Hướng dẫn thao tác bằng tiếng Anh
├── tutorial_vi.md               # Hướng dẫn thao tác bằng tiếng Việt
├── Project_Structure.md         # Tài liệu cấu trúc và vai trò module
├── launch.cmd / launch.sh       # Launcher cho Windows / Linux
├── launch.py                    # Chọn luồng thiết lập hoặc mở ứng dụng
├── main.py                      # Khởi tạo QApplication và cửa sổ chính
├── main_window.py               # Điều phối dataset, UI, công cụ, Save và Undo/Redo
├── image_grid.py                # Lưới ảo hóa, thẻ ảnh và phần vẽ tag
├── tag_panel.py                 # Tìm kiếm/lọc tag và thao tác theo tag
├── preview_dock.py              # Xem ảnh, pan và zoom
├── history_window.py            # Dock lịch sử thao tác
├── settings_dialog.py           # Chung, Lịch sử, Phím tắt, Không gian làm việc
├── dialogs.py                  # Các hộp thoại chung
├── requirements.txt            # Thư viện cho giao diện
├── requirements-local.txt      # Thư viện bổ sung để chạy WD14 Local
├── libs/
│   ├── app_paths.py
│   ├── backup_manager.py
│   ├── dataset_config.py
│   ├── file_formats.py
│   ├── file_ops.py
│   ├── folder_loader.py
│   ├── history_manager.py
│   ├── i18n.py
│   ├── settings_manager.py
│   ├── shortcut_manager.py
│   ├── table_icon.py
│   ├── thumbnail_loader.py
│   ├── workspace_manager.py
│   └── shared/draggable_list.py
├── tools/
│   ├── calculator_dataset.py
│   ├── dict_tags.py
│   ├── external_tagger.py
│   ├── remove_duplicate_tags.py
│   ├── replace_tags.py
│   ├── resort_tag_window_operation.py
│   ├── tagger_logic.py
│   ├── tagger_worker.py
│   ├── underscore_swap.py
│   └── waifu_tagger_window.py
├── lang/                       # en, vi, zh, ko, ja, ru
├── icons/                      # Icon SVG của ứng dụng và các nút
├── src/                        # Screenshot và tài nguyên minh họa
└── tests/                      # Automated testing và benchmark
```

## Các module điều phối và giao diện

| Module | Vai trò |
|---|---|
| [launch.py](launch.py) | Với `--setup`, tạo `.venv` và cài thư viện giao diện; sau đó gọi ứng dụng. Hai launcher của hệ điều hành chọn Python phù hợp. |
| [main.py](main.py) | Khởi tạo Qt, icon, ngôn ngữ, phiên bản và nhận đường dẫn dataset từ dòng lệnh. |
| [main_window.py](main_window.py) | Nối tín hiệu UI với thao tác; quản lý ảnh đang mở, cache theo thư mục, lưu caption và điều hướng Undo/Redo. |
| [image_grid.py](image_grid.py) | Tạo thẻ quanh vùng đang xem, tính bố cục theo chế độ lưới/chiều cao và vẽ tag có thể tương tác. |
| [tag_panel.py](tag_panel.py) | Hiển thị tag và số lượng, tìm kiếm, bộ lọc và lựa chọn tag dùng trong batch tool. |
| [settings_dialog.py](settings_dialog.py) | Cho người dùng thay đổi cài đặt và quản lý phím tắt/workspace. |
| [preview_dock.py](preview_dock.py), [history_window.py](history_window.py) | Hai dock cho việc kiểm tra ảnh và theo dõi lịch sử chỉnh sửa. |

## Tiện ích và quản lý trong `libs/`

| Module | Vai trò |
|---|---|
| [app_paths.py](libs/app_paths.py) | Xác định đường dẫn tài nguyên và dữ liệu cấu hình. |
| [file_formats.py](libs/file_formats.py) | Định dạng ảnh hỗ trợ và kiểm tra phần mở rộng caption. |
| [file_ops.py](libs/file_ops.py) | Đọc ảnh/caption, ghi caption và kết hợp bước dataset backup trước khi Save. |
| [backup_manager.py](libs/backup_manager.py) | Tạo snapshot thư mục cùng manifest; đánh dấu bản chưa hoàn tất bằng `.partial`. |
| [folder_loader.py](libs/folder_loader.py) | Đọc dữ liệu thư mục trên worker và trả kết quả về giao diện. |
| [thumbnail_loader.py](libs/thumbnail_loader.py) | Giải mã thumbnail nền và quản lý cache có giới hạn bộ nhớ. |
| [history_manager.py](libs/history_manager.py) | Lưu chênh lệch tag trước/sau theo chỉ số ảnh; quản lý hai stack Undo/Redo. Đường dẫn thư mục tương ứng do `main_window.py` quản lý. |
| [settings_manager.py](libs/settings_manager.py) | Dùng QSettings để đọc/ghi cấu hình dùng chung và phát tín hiệu thay đổi. |
| [shortcut_manager.py](libs/shortcut_manager.py) | Khai báo phím mặc định, đọc phím tùy chỉnh, kiểm tra xung đột và gán vào QAction. |
| [workspace_manager.py](libs/workspace_manager.py) | Lưu/khôi phục trạng thái dock và thói quen thao tác; nhập/xuất JSON, tự động lưu và reset. |
| [dataset_config.py](libs/dataset_config.py) | Kiểm tra dataset và sinh TOML theo cấu trúc trainer mà Calculator chọn. |
| [i18n.py](libs/i18n.py) | Nạp bản dịch trong `lang/`, chuẩn hóa mã ngôn ngữ và cung cấp hàm `tr()`. |
| [table_icon.py](libs/table_icon.py) | Ánh xạ tên icon và tạo icon phù hợp màu giao diện. |
| [shared/draggable_list.py](libs/shared/draggable_list.py) | Widget danh sách kéo thả dùng lại trong công cụ sắp xếp. |

## Công cụ trong `tools/`

| Module | Vai trò |
|---|---|
| [waifu_tagger_window.py](tools/waifu_tagger_window.py) | Giao diện chọn chế độ WD14, model, ngưỡng nhận diện và phạm vi gắn tag. |
| [tagger_logic.py](tools/tagger_logic.py) | Logic chạy model ONNX và xử lý kết quả tag. |
| [external_tagger.py](tools/external_tagger.py) | Tìm Python/model của tool đã cài và khởi chạy tiến trình suy luận. |
| [tagger_worker.py](tools/tagger_worker.py) | Điểm vào tiến trình dùng Python của tool bên ngoài; trả tiến độ và kết quả cho TKtagger. |
| [calculator_dataset.py](tools/calculator_dataset.py) | Quét thư mục, tính repeat/bước ước tính và xuất TOML qua `dataset_config.py`. |
| [dict_tags.py](tools/dict_tags.py) | Quản lý nhóm từ điển và mở rộng tag ảo. |
| [replace_tags.py](tools/replace_tags.py), [remove_duplicate_tags.py](tools/remove_duplicate_tags.py) | Thay thế tag theo quy tắc và loại bỏ tag trùng. |
| [resort_tag_window_operation.py](tools/resort_tag_window_operation.py) | Giao diện và logic sắp xếp tag, gồm thứ tự nhóm từ điển. |
| [underscore_swap.py](tools/underscore_swap.py) | Chuyển đổi dấu gạch dưới và khoảng trắng trong tag. |

## Luồng dữ liệu chính

1. Launcher mở `main.py`; cửa sổ chính khởi tạo UI, cài đặt và workspace.
2. `folder_loader.py` đọc metadata ảnh/caption. `image_grid.py` chỉ tạo các thẻ cần hiển thị và yêu cầu thumbnail từ worker.
3. Thao tác chỉnh tag cập nhật dữ liệu trong RAM và ghi chênh lệch vào HistoryManager. Cache giữ dữ liệu của các thư mục đã làm việc trong phiên.
4. Save gom ảnh đã thay đổi, hoàn tất backup rồi ghi caption qua `file_ops.py`.
5. WD14 trả kết quả về cửa sổ chính để cập nhật RAM/cache. Calculator xuất cấu hình dataset TOML; workspace xuất bố cục JSON.

## Cấu hình, tài nguyên và kiểm thử

- `settings.ini`: cài đặt người dùng, phím tắt và workspace đã lưu. Chạy từ mã nguồn mặc định dùng thư mục dự án; có thể đổi nơi lưu bằng `TKTAGGER_DATA_DIR`.
- `lang/*.json`: sáu bản dịch giao diện. Các bản dịch cần giữ cùng khóa và placeholder.
- `icons/tktagger.svg`: icon ứng dụng. `src/Screenshot_20260831_112158.png` là ảnh minh họa trong README.
- `tests/`: automated testing cho dữ liệu, UI, Undo/Redo, export và workspace; có thêm benchmark lưới ảnh. Xem [hướng dẫn kiểm thử](tests/README.md).
- `.tktagger-backups/`: snapshot nằm cạnh thư mục dataset được lưu. Đây là dữ liệu phục hồi do ứng dụng tạo, tách khỏi mã nguồn.
