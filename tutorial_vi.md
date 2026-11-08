# Hướng dẫn sử dụng TKtagger Desktop

[English](tutorial.md) · **Tiếng Việt**

[README tiếng Việt](README_VI.md) · [Cấu trúc dự án](Project_Structure.md)

Hướng dẫn này dành cho người đã biết dataset, caption/tag và các khái niệm huấn luyện AI cơ bản. Mở ứng dụng bằng `launch.cmd` trên Windows hoặc `sh ./launch.sh` trên Linux; xem README nếu cần chạy `--setup` lần đầu.

## 1. Phím tắt mặc định

| Phím tắt | Thao tác |
|---|---|
| `Ctrl+O` | Mở thư mục dataset |
| `Ctrl+S` | Lưu caption đã thay đổi |
| `Ctrl+Z` | Undo — hoàn tác |
| `Ctrl+Y` | Redo — làm lại |
| `Ctrl+A` | Chọn tất cả ảnh |
| `Ctrl+D` | Bỏ chọn tất cả ảnh |
| `Ctrl+I` | Đảo lựa chọn ảnh |
| `Ctrl+E` hoặc `F5` | Xóa tag trùng |
| `Ctrl+R` hoặc `F6` | Sắp xếp tag |
| `Ctrl+Shift+U` | Chuyển dấu gạch dưới và khoảng trắng |
| `Ctrl+T` hoặc `F8` | Mở WD14 Tagger |
| `Ctrl+Shift+D` hoặc `F9` | Mở Dataset Calculator |

Các phím chuẩn như Undo/Redo có thể khác theo hệ điều hành; phím đang gán được hiển thị trong menu. Khi con trỏ nằm trong ô nhập, các thao tác chỉnh văn bản có thể được ô nhập xử lý.

Vào **Cài đặt → Phím tắt** để gán phím chính/phím thay thế, xóa phím gán hoặc khôi phục mặc định. Các lệnh trong menu Từ điển và Trợ giúp không nằm trong danh sách tùy chỉnh.

## 2. Mở folder và làm quen giao diện

1. Chọn **Tệp → Mở thư mục** hoặc nhấn `Ctrl+O`.
2. Chọn thư mục gốc dataset, rồi bấm một thư mục trong cây để xem ảnh bên trong.
3. Kiểm tra phần mở rộng caption tại **Cài đặt → Chung**: `.txt`, `.cap` hoặc tùy chỉnh. Khi đổi phần mở rộng, làm theo thông báo khởi động lại của ứng dụng.

Caption dùng cùng tên gốc với ảnh, ví dụ `image_001.png` và `image_001.txt`. Tag được phân cách bằng dấu phẩy.

| Thành phần | Cách dùng |
|---|---|
| Cây thư mục | Chuyển giữa các thư mục trong dataset. |
| Lưới ảnh | Bấm thẻ ảnh để chọn/bỏ chọn; dùng các nút chọn tất cả, đảo chọn hoặc bỏ chọn. |
| Bảng tag | Tìm tag, chọn tag lọc và mở thao tác xóa/thay thế tag. |
| Thanh input phía dưới | Nhập tag để thêm/xóa trên các ảnh đã chọn. |
| Preview | Bấm nút xem trước trên thẻ ảnh; dùng khung preview để xem và zoom. |
| Lịch sử | Mở từ menu Chỉnh sửa hoặc nút History để xem và thực hiện Undo/Redo. |

Lựa chọn **ảnh** trong lưới và lựa chọn **tag** trong bảng tag là hai phạm vi khác nhau. Hãy kiểm tra phạm vi của công cụ trước khi áp dụng.

Trong **Cài đặt → Chung**, chọn lưới **Cổ điển** để chỉnh số cột thủ công hoặc **Tự động điều chỉnh** để tận dụng chiều rộng. Chọn chiều cao **Vừa phải**, **Dài hơn** hoặc **Đầy đủ nội dung thẻ** theo lượng tag cần đọc.

## 3. Gắn tag từ thanh input: Begin / Last

1. Chọn một hoặc nhiều ảnh trong lưới.
2. Nhập tag, ví dụ `blue_sky, outdoors`.
3. Chọn **Begin / Đầu** hoặc **Last / Cuối**, rồi bấm **Thêm tag**.

Với danh sách ban đầu là `landscape`:

```text
Begin: blue_sky, outdoors, landscape
Last:  landscape, blue_sky, outdoors
```

Thứ tự tag mới được giữ đúng như khi nhập. Tag trùng trong input hoặc đã có trên ảnh sẽ được bỏ qua; tag đã có giữ vị trí hiện tại. Sau thao tác hàng loạt, ứng dụng bỏ chọn ảnh; chọn lại trước thao tác tiếp theo.

Để xóa tag trên ảnh đã chọn, nhập các tag vào cùng thanh input rồi bấm **Xóa tag**. Ô nhập trên từng thẻ ảnh thêm tag vào riêng ảnh đó khi nhấn Enter. Trên phần tag của thẻ ảnh:

- **Chuột phải:** đưa tag vào thanh input chung.
- **Chuột giữa:** yêu cầu xóa tag đó khỏi ảnh.

Dùng Undo/Redo để kiểm tra lại thay đổi; bấm **Lưu** khi muốn ghi caption ra đĩa.

## 4. Sử dụng batch tool

| Công cụ | Cách dùng cơ bản và phạm vi |
|---|---|
| Xóa tag trùng | Mở từ menu Công cụ hoặc `F5`; xử lý danh sách ảnh đang nạp của thư mục hiện tại. |
| Thay thế tag | Chọn tag trong bảng tag, bấm Thay thế, nhập giá trị mới và xác nhận; thay trên các ảnh đang nạp có tag phù hợp. |
| Sắp xếp tag | Mở bằng `F6`, chọn quy tắc/thứ tự nhóm từ điển trong cửa sổ công cụ, rồi áp dụng. |
| Gạch dưới/khoảng trắng | Chọn chiều chuyển đổi, ví dụ `blue_sky` ↔ `blue sky`; áp dụng cho các ảnh đang nạp. |
| Xóa sạch tag của ảnh đã chọn | Chọn ảnh rồi dùng lệnh tương ứng trong menu Công cụ; đọc hộp xác nhận trước khi tiếp tục. |

Các công cụ chỉnh tag cập nhật dữ liệu trong bộ nhớ và lịch sử. Kiểm tra kết quả trên lưới trước khi **Lưu**. Việc chọn một vài ảnh không tự giới hạn mọi batch tool vào những ảnh đó; phạm vi phụ thuộc từng công cụ.

## 5. WD14 Tagger

Mở bằng `Ctrl+T` hoặc `F8`. Chọn chế độ thực thi, model, ngưỡng nhận diện tag chung/nhân vật và các tùy chọn như thêm vào caption hiện có hoặc bỏ qua ảnh đã có caption. Kiểm tra phạm vi thư mục trước khi chạy; **Bao gồm thư mục con** lấy phạm vi từ thư mục gốc dataset trong cây.

### Chạy Local trong môi trường TKtagger

Nếu đã tạo `.venv` bằng launcher `--setup`, cài thêm thư viện suy luận:

```powershell
# Windows
.\.venv\Scripts\python.exe -m pip install -r requirements-local.txt
```

```bash
# Linux
./.venv/bin/python -m pip install -r requirements-local.txt
```

Chọn **Local**, nhập repo model hoặc chọn cặp file **ONNX** và **selected_tags.csv** tương ứng, rồi chạy. Lấy model từ repo có thể cần tải file qua mạng. Kiểm tra tag sinh ra trước khi lưu caption.

### Reuse an installed tool — dùng lại tool đã cài

1. Chọn **Installed tool** trong WD14.
2. Chọn thư mục cài **kohya_ss** hoặc **sd-scripts**.
3. Chọn loại tool hoặc **Auto detect**, rồi bấm **Scan**.
4. Kiểm tra Python tìm được trong `.venv`, `venv` hoặc `env`. Nếu cần, chọn trực tiếp Python có môi trường suy luận hoạt động.
5. Chọn model ONNX được tìm thấy cùng `selected_tags.csv`, hoặc nhập hai đường dẫn thủ công.
6. Thiết lập tùy chọn gắn tag và chạy.

Chế độ này dùng Python và model có sẵn của tool để chạy worker TKtagger. Phần giao diện TKtagger chỉ cần các thư viện từ bước `--setup`; môi trường Python đã chọn cần có các thư viện suy luận phù hợp. Nếu tool hoặc môi trường đã được di chuyển, kiểm tra lại đường dẫn Python và model.

Kết quả WD14 được đưa vào bộ nhớ/cache từng thư mục, kể cả thư mục con chưa mở. Kiểm tra kết quả, dùng Undo/Redo khi cần và bấm **Lưu** để ghi caption.

## 6. Calculator: tính repeat và xuất TOML

1. Mở **Dataset Calculator** bằng `F9`.
2. Chọn trainer, phần mở rộng caption và độ phân giải; quét thư mục dataset.
3. Chọn các thư mục cần dùng, nhập tỷ lệ theo thứ tự dòng, ví dụ `1,2,3`.
4. Chỉnh batch/epochs để xem ước tính, rồi bấm **Tính toán**.
5. Bấm **Xuất TOML**, chọn nơi lưu file cấu hình dataset.

Calculator đếm ảnh PNG, JPG/JPEG, WebP và BMP trực tiếp trong từng thư mục. Mỗi ảnh trong thư mục xuất cần có caption đúng phần mở rộng đã chọn. Nếu thiếu caption hoặc số ảnh đã đổi, sửa dữ liệu rồi quét và tính lại.

File xuất có cấu trúc riêng cho **kohya_ss / sd-scripts** hoặc **Musubi Tuner**. Đường dẫn thư mục giữ nguyên; repeat được khai báo trong TOML. Chọn file này làm dataset config trong trainer. Model, optimizer và epochs huấn luyện thực tế được thiết lập trong trainer; số bước Calculator hiển thị là ước tính.

## 7. Lưu thói quen bố trí giao diện

Vào **Cài đặt → Không gian làm việc**:

- **Lưu:** ghi bố cục hiện tại để khôi phục khi mở ứng dụng.
- **Nhập / Xuất:** dùng file JSON để chuyển bố cục giữa các lần làm việc.
- **Tự động lưu:** ghi bố cục sau khi thao tác ổn định và khi đóng ứng dụng thành công; mặc định tắt.
- **Đặt lại:** khôi phục và lưu bố cục mặc định.

Các nút này áp dụng ngay. Bản lưu gồm cửa sổ, dock/tab, trạng thái ẩn/hiện, chế độ lưới, chiều cao thẻ, số cột thủ công và vị trí chèn tag. Nội dung dataset và lịch sử Undo/Redo thuộc phiên chỉnh sửa, không nằm trong file workspace.

## 8. Lưu caption và dataset backup

Bấm **Lưu** hoặc `Ctrl+S` để ghi caption thay đổi của các thư mục đang giữ trong phiên. Ứng dụng tạo snapshot đầy đủ cho từng thư mục bị ảnh hưởng trước khi ghi caption. Backup lỗi thì dừng lưu.

Backup nằm trong `.tktagger-backups` bên cạnh thư mục dataset được lưu. Mỗi snapshot hoàn tất có thư mục `data/` và `manifest.json`. Snapshot có hậu tố `.partial` là bản chưa hoàn tất.

Để khôi phục: đóng ứng dụng, giữ một bản thư mục hiện tại, chép nội dung `data/` của snapshot hoàn tất vào một thư mục trống, rồi mở thư mục đó bằng TKtagger. Backup được giữ cho đến khi bạn xóa nên cần theo dõi dung lượng ổ đĩa.
