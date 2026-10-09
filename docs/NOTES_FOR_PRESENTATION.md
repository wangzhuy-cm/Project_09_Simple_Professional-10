# Ghi chú kỹ thuật cho buổi trình bày

Tài liệu này dành cho nhóm và giảng viên. Các ghi chú về cách triển khai không xuất hiện trong luồng sử dụng mặc định.

## Vai trò của từng thành phần

- LLM: đọc mô tả thành bản nháp hồ sơ khi chọn AI trực tuyến; bổ sung nhận xét định tính cho báo cáo khi người dùng bật tùy chọn.
- Python: chuẩn hóa và kiểm tra dữ liệu, tính dòng tiền, ba kịch bản, what-if, stress test, biểu đồ và PDF.
- Người dùng: bổ sung dữ liệu thiếu, sửa bản nháp, xác nhận hồ sơ và giả định, duyệt nội dung báo cáo.
- Bảng Mục tiêu, nguồn lực và ràng buộc hiện do Python tổng hợp. Chưa chứng minh LLM phân rã mục tiêu trực tuyến.

## Dữ liệu mẫu và minh chứng

- Hồ sơ mẫu dùng bản nháp chuẩn bị sẵn; không phải phản hồi API đã ghi lại.
- Demo ngoại tuyến chứng minh luồng ứng dụng và phép tính; không đo độ chính xác LLM.
- Chưa gọi API thật trong các lần sửa và kiểm thử này. Không công bố điểm chất lượng LLM trực tuyến.
- 58 kiểm thử liên quan đạt sau khi rút gọn giao diện: test_goal_review, test_sapphire_workflow, test_integration, test_person1_data_and_ui.
- AppTest kiểm tra trạng thái/widget/luồng và PDF; chưa nghiệm thu hình ảnh giao diện desktop/mobile trên trình duyệt.

## Các giả định cần giải thích nếu được hỏi

- Mục tiêu nhập theo giá hôm nay, được điều chỉnh bởi lạm phát giả định.
- Khoản góp ghi nhận cuối tháng, lợi suất không phải cam kết.
- Nhu cầu thanh khoản và tăng thu nhập được ghi nhận nhưng chưa tác động công thức.
- Thiếu hụt sinh hoạt khi stress chưa tự rút từ tiền mục tiêu hoặc quỹ dự phòng; phải có nguồn bù để diễn giải kết quả theo điều kiện đó.
- Các mức lợi suất/lạm phát mặc định là giả định mô phỏng, chưa được xác minh là dữ liệu thị trường hiện hành.

## Bảng đánh giá kỹ thuật tùy chọn

Mặc định bảng Vai trò LLM và minh chứng hệ thống được ẩn. Nhóm có thể mở lại riêng cho buổi nghiệm thu trên macOS/Linux:

```bash
PROJECT09_SHOW_TECHNICAL=1 python -m streamlit run app.py
```

Không bật biến này thì giao diện chỉ hiện phần lập kế hoạch. Mở bảng đánh giá không tự chạy LLM; chỉ nút đánh giá trực tuyến mới gọi API. Không cần mở bảng khi trình bày với khách hàng.

## Thông tin vẫn hiển thị cho người dùng

- Hồ sơ mẫu, hồ sơ nhập thủ công hoặc bản nháp AI được ghi nhãn đúng nguồn.
- Nhận xét AI và giải thích tiêu chuẩn được phân biệt, kể cả khi AI không khả dụng.
- Giả định, cảnh báo khả năng chi trả, giới hạn tính toán và các bước xác nhận vẫn hiển thị.
- Khi bật AI, thông báo gửi dữ liệu đến OpenAI và khả năng phát sinh chi phí vẫn hiển thị trước thao tác.

Không dùng việc ẩn ghi chú kỹ thuật để trình bày mẫu soạn sẵn thành AI xử lý thật.
