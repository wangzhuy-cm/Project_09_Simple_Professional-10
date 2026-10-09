# Luồng trạng thái phiên

## Electric Sapphire

Xác nhận ở Bước 2 chỉ cho phép mô phỏng. Bước 3 có fingerprint của hồ sơ + giả định + phép thử; khi khác fingerprint đã duyệt, `assumptions_confirmed=False`. Người dùng vẫn xem trước được nhưng không được xuất PDF. Chỉ đổi phương án đang xem không thay kế hoạch cơ sở hoặc làm mất xác nhận. Bước 4 kiểm tra cả xác nhận hồ sơ và giả định rồi yêu cầu duyệt nội dung báo cáo.

Các khóa widget chỉnh sửa được giữ qua điều hướng. Refresh/mất phiên vẫn có thể mất dữ liệu; chưa có lưu trữ tài khoản. Bảng dưới lưu phân công module ban đầu, đọc cùng quy tắc mới này.

| Bước giao diện | Dữ liệu nhận | Module | Kết quả và quy tắc |
|---|---|---|---|
| Hồ sơ tài chính | Form / mô tả / fixture | Người 1: `ui/profile_page.py`, `src/schemas.py`; Người 4 trích xuất | `profile_draft`, giữ None cho ô trống; thay đổi fingerprint xóa review, scenario, report |
| Xác nhận dữ liệu | Hồ sơ nháp và giả định | Người 4: `ui/review_page.py`, `src/validation.py` | `integrated_review_bundle` chỉ khi VALID/WARNING, `can_simulate` và một xác nhận dữ liệu chung; sửa một ô hủy xác nhận và bundle phụ thuộc |
| Mô phỏng & phân tích | Bundle đã duyệt + snapshot tham chiếu 24/09/2026 | Người 2: `src/calculations.py`, `ui/cashflow_page.py`; Người 3: `src/scenarios.py`, `src/stress_test.py`, `src/charts.py`, `ui/scenario_page.py`; nguồn: `src/market_reference.py` | Base từ `scenarios.base`; assumptions cuối được validate lại và tự cập nhật; fingerprint mới xóa report cũ; what-if không ghi đè profile |
| Giải thích & báo cáo | Bundle mô phỏng hiện hành | Người 5: `src/llm_explanation.py`, `src/report_generator.py`, `ui/report_page.py` | Fingerprint thay đổi xóa giải thích/PDF; giải thích có kiểm tra số và báo cáo cần xác nhận cuối |
| Đánh giá hệ thống | 20 hồ sơ test + API tùy chọn | `src/evaluation_runner.py`, `ui/evaluation_panel.py` | Baseline luôn đo tại máy; live metrics chỉ sinh sau khi người dùng bấm chạy và API trả kết quả thật; CSV không chứa điểm live giả |

`app.py` điều phối và hiển thị năm khu vực (Tổng quan, Hồ sơ, Xác nhận, Mô phỏng, Báo cáo). Menu ngang cho phép quay lại; bước chưa đủ dữ liệu hiển thị lý do và không chạy module phụ thuộc. Reset có xác nhận trong popover Tiến độ, chỉ xóa key phiên của workflow và UI nhóm. Refresh trình duyệt giữ state trong phiên Streamlit; mất kết nối hoặc mở phiên mới không bảo đảm duy trì dữ liệu.
