# Bản làm lại Electric Sapphire

## Giao diện

| Vai trò | Màu |
|---|---|
| Nền tối / nhận diện | `#070B1A`, `#111D3F` |
| Nút chính / liên kết | `#2563EB` (chữ trắng); liên kết `#1D4ED8` |
| Phương án cơ sở | `#06B6D4` |
| Phương án tích cực | `#8B5CF6` |
| Phương án thận trọng | `#94A3B8` |
| Mục tiêu | `#F4C76B`; nhãn/đường trên nền sáng dùng `#B77915` |
| Cú sốc / rủi ro | `#F06464` |
| Nền trang / bề mặt | `#F4F7FF`, `#FFFFFF`, `#EEF4FF` |
| Chữ / chữ phụ / đường viền | `#111827`, `#5F6F85`, `#D7E2F1` |

Chữ dùng Liberation Sans nhúng, thống nhất web/PDF và chạy offline. Bố cục trang chủ giữ nguyên thành phần. Các trang trong dùng masthead nhỏ, nhóm form rõ ràng và nội dung nâng cao thu gọn. Không dùng màu để biểu đạt trạng thái một mình: luôn có tên phương án/kết luận/nhãn.

## Những lỗi đã sửa

- Bỏ tự xác nhận giả định; fingerprint riêng cho hồ sơ, giả định và phép thử. Báo cáo cần xác nhận hiện hành.
- Giữ trạng thái khi chuyển trang, dữ liệu đã sửa tại Xác nhận được điền lại khi quay về Hồ sơ.
- Thu nhập/chi tiêu chưa đủ thành phần không được cộng như thể ô trống bằng 0.
- Đưa nhu cầu rút tiền ra khỏi nhóm “không bắt buộc” vì schema hiện vẫn yêu cầu trường này. Nêu rõ chưa mô phỏng thanh khoản.
- Sửa lời nhắc nhập 0; giải thích giá trị hiện tại/tương lai của mục tiêu và giới hạn tăng thu nhập.
- Thêm đối chiếu bản nháp/nguồn trích dẫn; kiểm tra thêm trường hợp lấy đúng số nhưng từ ngữ cảnh sai khoản thu/chi. Đây chưa phải kiểm chứng ngữ nghĩa hoàn chỉnh.
- Tách LLM/demo/Python; không tự gọi API lúc xuất báo cáo. Nội dung LLM ở sau mục cảnh báo không còn bị che mất.
- Thể hiện rõ nguồn, ngày và trạng thái chưa xác minh của snapshot; ngày cập nhật chấp nhận ISO hợp lệ thay vì khóa cứng một ngày.
- Giảm chart chính xuống 3; đổi phương án cập nhật cả 3. Màu chart nhất quán. Dòng tiền bằng 0 không hiển thị số giả 1 đồng.
- PDF nói rõ đầu vào thay đổi; ghi tháng đạt trước/sau stress và độ trễ so với hạn gốc; phân phạm vi cảnh báo; đường mục tiêu trên chart đi theo lạm phát.
- PDF không ép mọi hồ sơ vào đúng 3 trang. Bản dài được chuyển trang; preview trong web render từ chính bytes PDF vừa tạo.

## Kịch bản trình bày không cần API

1. Hồ sơ → Mô tả tự nhiên → Minh họa ngoại tuyến → P001 → Trích xuất hồ sơ.
2. Xác nhận → mở Đối chiếu mô tả và bản nháp. Nói: “Đây là dữ liệu chuẩn bị sẵn để minh họa vai trò LLM; chưa phải phản hồi LLM thật.”
3. Sửa một khoản thu nhập, xác nhận rồi qua Kế hoạch. Chọn ba phương án: giải thích và chart thay đổi theo dữ liệu Python tính thật.
4. Thay lạm phát, chỉ ra ô xác nhận bị bỏ và nút Báo cáo bị khóa. Tích xác nhận để tiếp tục.
5. Báo cáo → giữ AI trực tuyến tắt → tạo giải thích → xác nhận → tạo PDF → xem từng trang.
6. Mở “Vai trò LLM và minh chứng hệ thống”. Giải thích: LLM giảm thao tác nhập và hỗ trợ ngôn ngữ; Python giữ công thức/kiểm tra; con người duyệt đầu vào và kết quả. Chưa gọi API thì chất lượng LLM là **chưa đo**, không phải 0% hay 100%.

Không cần chạy bộ đánh giá live để thể hiện kiến trúc. Khi có hạn mức trở lại, cần đánh giá phản hồi thật mới đưa ra tuyên bố về hiệu quả LLM. Không dùng tỷ lệ pass pytest hoặc schema baseline làm độ chính xác AI.

## Không thay đổi

`src/calculations.py`, `src/scenarios.py`, `src/stress_test.py`, `src/schemas.py` được giữ nguyên nội dung từ ZIP đầu vào. Không thêm quản lý danh mục, sản phẩm đầu tư, Monte Carlo, đăng nhập hoặc cơ sở dữ liệu ngoài phạm vi Project 09.
