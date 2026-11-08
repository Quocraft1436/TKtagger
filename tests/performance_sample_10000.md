# Mẫu hiệu năng: 10.000 ảnh giả

Đo ngày 2026-11-07 trên Linux, Python 3.14.9, Qt offscreen. Dùng 10.000 PNG
256×256 và 10.000 caption thật trên ổ đĩa, 25 tag/ảnh. Nội dung ảnh lấy từ 16
mẫu màu lặp lại; mỗi file có đường dẫn riêng. Filesystem cache nóng sau khi tạo
ảnh. Không chạy AI, không Save và không thay đổi dataset của người dùng.

## Cách tái hiện

Module benchmark đã đổi tên thành `tests.gui_benchmark`; số đo mẫu được giữ nguyên.

```bash
QT_QPA_PLATFORM=offscreen python -m tests.gui_benchmark --storage disk --count 10000 --size 256 --tags 24 --mode virtual-grid --max-render-seconds 300 --max-rss-mb 1024
```

[JSON số đo](performance_sample_10000.json) giữ kết quả của lần chạy mẫu;
artifact/screenshot của từng lần chạy nằm trong `tests/artifacts/` và được Git ignore.

## Kết quả lưới ảo

| Chỉ số | Kết quả |
|---|---:|
| Đọc metadata/caption | 0,121 giây |
| Hiện vùng ảnh đầu tiên sau khi nạp metadata | 0,130 giây |
| Số ảnh đã giải mã và paint qua thao tác cuộn | 10.000 / 10.000 |
| Cuộn, giải mã và paint đủ toàn bộ tập | 83,11 giây |
| Card tồn tại đồng thời tối đa | 18 |
| Cache thumbnail ở cuối bài | 63,93 MiB / giới hạn 64 MiB |
| RAM đỉnh của tiến trình (RSS, gồm các bước benchmark) | 196,38 MiB |
| Khoảng cách heartbeat UI dài nhất | 40,33 ms |
| Thêm tag một ảnh, cập nhật panel và paint | 17,22 ms |
| Undo / Redo | 11,24 / 10,25 ms |
| Số lần dựng lại lưới khi thêm tag + Undo + Redo | 0 |
| Số ảnh được lưu trong history entry của thao tác đó | 1 |

83 giây là thời gian chương trình kiểm thử cuộn và vẽ **toàn bộ** ảnh; giao diện
không phải đợi 83 giây mới sử dụng được. `load_seconds` đo hàm đọc riêng, còn
ứng dụng thật chạy hàm này ở worker.

## Đối chiếu bằng MainWindow thật

Dùng cùng dataset đã tạo, với event loop Qt thật và các panel/menu đầy đủ:

| Chỉ số | Kết quả |
|---|---:|
| Từ yêu cầu mở folder đến thumbnail đầu tiên, gồm đọc metadata | 0,203 giây |
| Card tồn tại ở kích thước cửa sổ mặc định | 9 |
| Thêm tag một ảnh, cập nhật panel và paint | 21,02 ms |
| Undo | 16,22 ms |
| Khoảng cách heartbeat UI dài nhất trong bài | 61,93 ms |
| Dựng lại lưới sau thêm tag và Undo | 0 |
| Ảnh mang cờ modified sau Undo | 1 |

Bài đối chiếu không bấm Save, không ghi caption hoặc settings. Đây là smoke test
và số đo đơn lẻ, không phải thống kê p95 của thao tác người dùng.

## Các thay đổi xử lý điểm nghẽn

| Điểm nghẽn | Cách xử lý |
|---|---|
| Widget cho mọi ảnh | Chỉ tạo card ở viewport cộng hàng đệm; lưu lựa chọn theo chỉ số dữ liệu, độc lập với card. Thanh cuộn ánh xạ tọa độ logic để không vượt giới hạn chiều cao QWidget. |
| Sửa tag dựng lại mọi card | Cập nhật card đang tồn tại, đếm tag theo delta của history; bộ lọc không đổi thì không dựng lại. |
| Signal checkbox gây refresh lặp | Giữ bộ lọc trong TagPanel khi cập nhật; checkbox mới được đặt trạng thái trước khi nối signal. Thay đổi khi có bộ lọc được gộp qua timer. |
| Giải mã ảnh trên UI | Worker giải mã thành QImage, chuyển kết quả qua signal; QPixmap và widget được cập nhật ở luồng UI. Tối đa hai yêu cầu thumbnail đang chạy trên mỗi lưới. |
| Mất thumbnail qua refresh | LRU cache tối đa 64 MiB được giữ qua các lần dựng lại card. Hàng đợi chỉ phục vụ vùng hiện tại, không xếp sẵn 10.000 ảnh. |
| Undo giữ toàn bộ tag | Thao tác một ảnh/nhóm chọn chỉ chụp ứng viên tương ứng; history entry chỉ giữ các ảnh có tag thay đổi. |
| Undo đánh dấu mọi ảnh | Undo/Redo chỉ áp dụng và đặt modified cho các chỉ số trong delta. |
| Nạp folder/cây thư mục đồng bộ | Đọc metadata/caption ở worker; chỉ đưa dữ liệu vào UI khi đọc thành công. Cây thư mục tải nhánh khi mở, không duyệt đệ quy toàn bộ từ đầu. |

Card dùng vùng tag có thanh cuộn riêng cao 120 px để chiều cao hàng ổn định;
các tag dài vẫn truy cập được, không bị xóa khỏi dữ liệu.

## Giới hạn diễn giải

Chưa đo trước/sau trên cùng baseline, nên không đưa ra hệ số tăng tốc. Không suy
kết quả 10.000 ảnh giả thành cam kết cho một triệu ảnh thật, ảnh độ phân giải cao,
ổ đĩa lạnh/chậm hoặc GPU hiển thị. Metadata vẫn nằm trong RAM; phân nhóm theo bộ
lọc và công cụ sửa toàn bộ dataset vẫn phải duyệt dữ liệu. Danh sách tag riêng
biệt rất lớn chưa được ảo hóa.
