# ATE — kiểm thử tự động và stress test ảnh giả

Chạy từ thư mục gốc dự án, dùng Python đã cài PySide6. Không cần model AI,
Pillow, pytest hay kết nối mạng.

Chạy toàn bộ ATE (unit/regression tests, lưới ảo 10.000 ảnh và các lô nhỏ):

```bash
python -m tests.run_ate
```

Mặc định tạo 16 mẫu PNG trong RAM; mỗi ảnh có metadata riêng, Qt giải mã và vẽ
qua ImageGrid/ImageCard thật. Lưới chỉ tạo card trong viewport cộng một hàng đệm,
không tạo widget cho toàn bộ dataset. Thumbnail dùng worker với cache tối đa
64 MiB. Không cần model AI, Pillow hay mạng; cần PySide6.

Bài mẫu 10.000 PNG và 10.000 caption trên ổ đĩa, 256×256, 25 tag/ảnh:

```bash
python -m tests.ate --storage disk --count 10000 --size 256 --tags 24 --mode virtual-grid --max-render-seconds 300 --max-rss-mb 1024
```

`--tags` là số tag chung, cộng thêm một tag nhóm cho mỗi ảnh. File PNG dùng 16
mẫu lặp lại; đây là ảnh giả, không đại diện ảnh lớn hoặc ổ đĩa chậm. File/caption
được tạo riêng cho từng ảnh trong thư mục kết quả mới; không sửa dataset thật.

Các lựa chọn khác:

```bash
python -m unittest discover -s tests -v
python -m tests.ate --count 10000 --mode virtual-grid
python -m tests.ate --count 1000 --mode batch --batch-size 100
python -m tests.run_ate --disk-count 10000
```

Mỗi lần chạy tạo `tests/artifacts/run_<timestamp>_<id>/` chứa `report.json`,
`render_preview.png`, và `dataset/` nếu chọn disk. Các artifact được ignore trong
Git. Báo cáo lưu thời gian tạo/nạp dữ liệu, first viewport, cuộn/vẽ đủ mọi ảnh,
RAM đỉnh của tiến trình, số card tối đa, cache thumbnail, độ trễ heartbeat UI,
thời gian sửa một ảnh/Undo/Redo bằng các hàm thật của MainWindow và số ảnh được
lưu trong history entry. Sửa thử chỉ thay đổi RAM, không Save caption ra đĩa.

`first_view_seconds` tính sau khi metadata đã nạp. `load_seconds` đo hàm đọc
metadata riêng; trong ứng dụng thật hàm này chạy trên worker. Disk test dùng
filesystem cache nóng sau khi tạo ảnh. RAM test không đo filesystem IO.
`render_seconds` là cuộn qua toàn bộ lưới, giải mã và paint đủ mọi ảnh, không phải
thời gian phải đợi trước khi giao diện sử dụng được. `batch` thay dataset theo
lô; `virtual-grid` giữ toàn bộ metadata trong một lưới. `full-grid` là tên cũ được
giữ tương thích và hiện cũng dùng lưới ảo; không còn chế độ tạo mọi widget.

Không suy kết quả 10.000 ảnh thành cam kết chạy một triệu ảnh. Metadata, bộ lọc
và các thao tác sửa toàn bộ dataset vẫn tốn thời gian/RAM theo kích thước dataset;
lịch sử lưu delta nhưng công cụ sửa toàn bộ có thể phải chụp các ứng viên trên
toàn bộ tập. Danh sách tag riêng biệt rất lớn cũng chưa được ảo hóa.

## Backup dữ liệu

Trước Save, mỗi folder có ảnh thay đổi được sao chép đầy đủ vào
`<parent>/.tktagger-backups/<folder>_<hash>/<timestamp>_<id>/data/`, kèm `manifest.json`.
Một Save nhiều ảnh chỉ tạo một snapshot mỗi folder, mọi snapshot hoàn tất
trước lần ghi đầu tiên. Đổi tên folder cũng backup trước khi đổi; bản sao giữ tên folder ban đầu.
Tagger local và chế độ dùng tool đã cài đều ghi vào thư mục tạm; kết quả được giữ
trong RAM/cache theo từng folder, dữ liệu thật chỉ được backup và ghi khi Save.
Chế độ dùng tool đã cài chạy Python của tool với model ONNX/CSV hiện có, không gọi API.
Các test `test_external_tagger` dùng subprocess thật với worker giả lập inference;
`test_tagger_results` kiểm tra cache, Save và Undo/Redo qua nhiều folder.

Backup lỗi thì không ghi. Snapshot lỗi mang hậu tố `.partial`. Caption được
ghi qua file tạm rồi thay thế nguyên tử; nếu một file trong batch ghi lỗi,
các file đã ghi trước đó vẫn được giữ, file chưa ghi vẫn có cờ modified.
Undo/redo và chỉnh tag trong RAM chưa thay đổi file, chỉ Save mới backup.
Cơ chế này áp dụng cho dataset, không phải mọi lần lưu cấu hình/preset.

Backup không chứa các thư mục `.tktagger-backups` cũ, giữ nguyên symlink
và không sao chép nội dung nằm ngoài folder qua symlink. Không ghi caption
qua symlink. Backup không tự xóa; cần dung lượng tương ứng toàn bộ dataset
cho mỗi thao tác lưu. Không sửa dataset bằng chương trình khác trong lúc
backup. Để khôi phục: đóng ứng dụng, giữ một bản của folder hiện tại, chép
nội dung `data/` của snapshot hoàn tất sang một folder trống rồi mở folder đó.
