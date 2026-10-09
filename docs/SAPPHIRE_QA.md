# Kiểm thử bản Electric Sapphire

## Đã kiểm tra

- Python 3.12.14, Streamlit 1.64.0; 58 gói thư viện tương thích qua dependency check.
- `compileall` cho app, src, ui, tests và scripts đạt.
- Bộ kiểm thử: **479 passed**, không lỗi. Gồm 459 test gốc (hai test được cập nhật để phản ánh xác nhận giả định mới), thêm 20 ca hồi quy.
- AppTest: mẫu P001 qua Xác nhận → Kế hoạch → Báo cáo → sinh bytes PDF và ảnh preview. Quay về Xác nhận giữ dữ liệu và ô xác nhận; quay về Hồ sơ điền lại giá trị mới sửa.
- AppTest: thay lạm phát bỏ xác nhận, vẫn tính preview nhưng khóa tạo báo cáo. Sửa hồ sơ vô hiệu hóa bundle phụ thuộc. Chọn phương án không làm mất xác nhận.
- AppTest: fixture có nhãn ngoại tuyến; giữ hợp đồng 15 trường; không coi ô trống thu nhập bằng 0.
- Kiểm tra code: chế độ diễn giải ngoại tuyến không gọi nhà cung cấp và không cần đọc khóa; bằng chứng trích xuất giữ ngoài schema hồ sơ.
- PDF: tạo lại P001, P019, mỗi mẫu 3 trang A4; render cả 6 trang bằng Poppler và kiểm tra trực quan. Không thấy chữ tiếng Việt bị lỗi, bảng tràn hoặc nội dung bị cắt. P019 thể hiện tháng 22 → 25, chậm 3 tháng so cơ sở và trễ 1 tháng so hạn 24.
- PDF dài: tên mục tiêu tiếng Việt dài vẫn xuất được; không còn chặn chỉ vì vượt 3 trang. Đây là test xuất file, không phải kiểm tra hình ảnh mọi đầu vào bất kỳ.
- Đối chiếu SHA-256: `src/calculations.py`, `src/scenarios.py`, `src/stress_test.py`, `src/schemas.py` trùng bản ZIP đầu vào.

## Giới hạn kiểm tra

- **Chưa nghiệm thu ảnh giao diện desktop/mobile trên trình duyệt.** Browser cloud chặn URL localhost (`ERR_BLOCKED_BY_CLIENT`); tải browser kiểm thử local không thành công. Không dùng ảnh PDF để thay cho bằng chứng giao diện web.
- AppTest kiểm tra luồng/state/widget, không kiểm chứng CSS, tỷ lệ hiển thị, responsive hoặc khả năng đọc chart trên màn hình nhỏ.
- Chưa gọi API thật. Không công bố điểm độ chính xác LLM, tốc độ LLM hoặc chất lượng nhận xét live. Các mock/fixture chỉ minh họa và kiểm thử phần mềm.
- Snapshot lãi suất/lạm phát chưa được xác minh lại với nguồn bên ngoài. Các giá trị đó được công khai là giả định giáo dục.
- Chưa triển khai lên hosting công khai; đây là gói web chạy local hoàn chỉnh.

## Checklist ngắn trên máy người dùng

1. Chạy web, xem Hồ sơ/Xác nhận/Kế hoạch/Báo cáo ở 1440 px và 390 px.
2. Xác nhận chữ tiếng Việt, thanh menu cuộn ngang trên mobile và không có dữ liệu bị cắt.
3. Chọn từng phương án: ba chart đổi đồng bộ; mở/đóng hai mục so sánh.
4. Sửa một giả định, xác nhận lại, tải PDF. Kiểm tra PDF và ảnh preview cùng dữ liệu.
5. Để AI trực tuyến tắt nếu chưa có hạn mức; toàn bộ luồng trên vẫn hoạt động.

PDF mẫu: `outputs/sample_report.pdf`, `docs/QA_P001_report.pdf`, `docs/QA_P019_report.pdf`. Ảnh PDF hiện tại có tên `QA_P001_pdf_page-1.png` đến `-3.png`, tương tự P019; đây không phải ảnh chụp web.
