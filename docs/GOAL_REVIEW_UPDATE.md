# Bổ sung bảng kiểm tra mục tiêu

## Cách xem phần mới

1. Chạy ứng dụng như hướng dẫn trong README.
2. Tải hồ sơ mẫu hoặc nhập thủ công rồi chuyển sang Xác nhận.
3. Đọc bảng Mục tiêu, nguồn lực và ràng buộc.
4. Mở Sửa thông tin, đổi số tiền mục tiêu; bảng cập nhật và cần xác nhận lại.
5. Xóa thu nhập phụ hoặc thời hạn: bảng nêu thiếu thông tin và bước tiếp theo bị khóa.

## Thay đổi

- Thêm bảng tổng hợp mục tiêu, thời hạn, nguồn lực, dòng tiền, ràng buộc, rủi ro/thanh khoản, lỗi/cảnh báo và câu hỏi bổ sung.
- Không tự coi dữ liệu thiếu là 0. Dòng tiền âm hiển thị thiếu hụt và giữ nguyên chính sách cảnh báo của bộ kiểm tra hiện tại.
- Không đổi schema 15 trường, công thức, kịch bản, stress test, mã trích xuất hoặc diễn giải LLM.
- Bảng là kết quả Python, không phải LLM. Không gọi API khi hiển thị bảng hoặc sửa hồ sơ.

## Kiểm tra đã thực hiện

- 27 kiểm thử đạt: tests/test_goal_review.py, tests/test_sapphire_workflow.py, tests/test_integration.py.
- Kiểm tra biên dịch các tệp mới/sửa đạt.
- So sánh byte với ZIP đầu vào: calculations.py, scenarios.py, stress_test.py, schemas.py, llm_extraction.py và llm_explanation.py không đổi.
- Streamlit AppTest kiểm tra widget/state và luồng PDF, không thay thế kiểm tra trực quan trong trình duyệt.
- Kiểm thử dùng Streamlit 1.64.0, OpenAI SDK 2.54.0, Plotly 6.9.0, pytest 9.1.1; thư viện phụ thuộc trong môi trường kiểm tra có thể khác requirements.txt. Chưa kiểm tra lại cài đặt mới toàn bộ phiên bản khóa của dự án.

## Phạm vi còn lại

Chưa gọi API thật; chưa chứng minh LLM phân rã mục tiêu hoặc chất lượng phản hồi trực tuyến. Hàm diễn đạt câu hỏi bằng AI chưa được nối vào giao diện; câu hỏi hiện tại vẫn do bộ kiểm tra Python tạo. Nhu cầu thanh khoản vẫn chỉ ghi nhận, chưa tác động công thức. Cần nghiệm thu trực tuyến riêng nếu thầy yêu cầu minh chứng LLM thật.

Gói ZIP mới bỏ môi trường .venv và cache. Giải nén vào thư mục riêng rồi chạy scripts/setup_and_run.sh để tạo môi trường tại máy; không chép đè lên thư mục đang chạy.
