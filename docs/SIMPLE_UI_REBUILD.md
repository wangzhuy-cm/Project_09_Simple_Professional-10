# Bản giao diện đơn giản và chuyên nghiệp

## Mục tiêu

Bản này giữ nguyên schema, validation, calculation engine, scenario engine,
stress test, API trích xuất, giải thích và báo cáo. Thay đổi chỉ tập trung vào
cách trình bày để phù hợp với sinh viên và người trẻ có kiến thức tài chính cơ
bản.

## Luồng người dùng

1. Nhập thông tin.
2. Kiểm tra thông tin hệ thống đã hiểu.
3. Xem kế hoạch, ba phương án và thử điều chỉnh.
4. Đọc giải thích và tải báo cáo.

## Thay đổi chính

- Trang Kiểm tra chỉ hiển thị sáu thông tin quan trọng. Form sửa, 15 trường kỹ
  thuật và giả định được đặt trong các vùng mở rộng.
- Không hiển thị trạng thái `VALID` như một thuật ngữ dành cho người dùng.
- Trang Kế hoạch trả lời trước ba câu hỏi: có đạt mục tiêu không, dự kiến có bao
  nhiêu và nên dành bao nhiêu mỗi tháng.
- What-if chỉ yêu cầu thu nhập, chi phí thiết yếu, thời hạn và số tiền dành mỗi
  tháng.
- Stress test dùng câu hỏi “Nếu thu nhập giảm?” với lựa chọn 10%, 20% hoặc 30%.
- Lợi suất, lạm phát, nguồn tham chiếu, bảng đầy đủ và công thức vẫn được giữ
  trong phần nâng cao để phục vụ kiểm tra và thuyết trình.
- Evaluation LLM được chuyển thành phụ lục kỹ thuật dành cho giảng viên, không
  chen vào báo cáo tài chính của người dùng.
- Điều hướng quay lại nằm ngay đầu mỗi bước; trang Báo cáo có lối tắt về Xác
  nhận dữ liệu.
- Trang Kế hoạch đưa bộ chọn ba phương án lên trước; mỗi lựa chọn có giải thích,
  KPI và biểu đồ riêng, không cần mở thêm tab.
- Dashboard mặc định chỉ giữ biểu đồ tiến độ mục tiêu và phân bổ dòng tiền.
  Biểu đồ so sánh cả ba phương án và bảng số liệu chi tiết nằm trong hai vùng
  mở rộng riêng để giữ trang ngắn và dễ đọc.
- Báo cáo PDF dùng bố cục ba trang hiện đại với KPI, biểu đồ vector, bảng so
  sánh phương án, kết quả stress và phần giải thích dành cho người dùng.
- Màn Báo cáo trên web được thiết kế thành dashboard premium: hero kết luận,
  bốn KPI, hai biểu đồ mặc định, phần dòng tiền thu gọn và tiến trình ba bước
  **Tạo giải thích → Xác nhận nội dung → Tải báo cáo**.
- Các ghi chú nội bộ như tên module, engine, schema, fixture, trạng thái kỹ
  thuật và mã lỗi đã được loại khỏi luồng người dùng; phụ lục đánh giá dành cho
  giảng viên vẫn được giữ riêng.

## Kiểm tra trong môi trường build

- `python3 -m compileall -q app.py src ui tests`: đạt.
- P001: VALID, 118.000.000 VND, đạt tháng 30 ở giả định 0%.
- P009: NEEDS_CLARIFICATION, bị chặn vì thiếu thời hạn.
- P019: baseline 130.000.000 VND; stress 118.000.000 VND; chậm 3 tháng.
- Đã chạy lại toàn bộ pytest/Streamlit AppTest trên Python 3.12.14:
  Bản hoàn thiện mới nhất đạt **459 passed, 0 failed**; HTTP health trả `ok`.
