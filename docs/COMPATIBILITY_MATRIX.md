# Project 09 - Bảng tương thích năm module

## Nguồn chính thức được dùng

| Thành viên | File sở hữu được tích hợp |
|---|---|
| Người 1 | `data/*`, `src/schemas.py`, `ui/profile_page.py`, hai test Người 1 |
| Người 2 | `src/calculations.py` bản FIXED, `ui/cashflow_page.py`, hai test và file Excel kiểm chứng |
| Người 3 | `config/scenario_defaults.json`, `src/scenarios.py`, `src/stress_test.py`, `src/charts.py`, `ui/scenario_page.py`, test scenarios |
| Người 4 | `src/llm_extraction.py`, `src/validation.py`, `ui/review_page.py`, test validation, `.env.example` |
| Người 5 | `src/llm_explanation.py`, `src/evaluation.py`, `src/report_generator.py`, `ui/report_page.py`, test LLM outputs, font, evaluation và PDF mẫu |

Không chép thư mục `demo` hoặc module tham chiếu của thành viên khác. Các bản gốc không bị sửa.

## Kết quả đối chiếu phụ thuộc

- `schemas.py` Người 1 trùng từng byte với bản Người 3 và Người 4 dùng để phát triển.
- `calculations.py` Người 2 FIXED trùng từng byte với bản Người 3 và Người 4 dùng để phát triển.
- `scenarios.py` và `scenario_defaults.json` Người 3 trùng từng byte với bản Người 4 dùng để phát triển.
- Bảy public API bắt buộc đều có đúng tên: `extract_profile`, `validate_profile`, `calculate_financial_metrics`, `build_scenarios`, `run_stress_test`, `generate_explanation`, `generate_report`.

## Hợp đồng dữ liệu cuối cùng

### FinancialProfile

Profile luôn có đúng 15 khóa:

`user_id`, `monthly_primary_income`, `monthly_other_income`, `monthly_essential_expense`, `monthly_discretionary_expense`, `monthly_debt_payment`, `current_savings`, `emergency_fund_reserved`, `goal_name`, `goal_amount`, `goal_horizon_months`, `risk_tolerance`, `liquidity_need`, `expected_income_growth`, `notes`.

- Tiền: số VND hữu hạn.
- Tỷ lệ: số thập phân theo năm.
- Thời hạn: số tháng nguyên.
- Dữ liệu chưa biết: `None`, không tự đổi thành 0.
- Risk/liquidity: `low`, `medium`, `high`.

### Assumptions

Chỉ dùng bốn khóa engine:

- `annual_return_rate`: bắt buộc.
- `annual_inflation_rate`: tùy chọn, mặc định engine bằng 0.
- `monthly_contribution`: tùy chọn; `None` nghĩa là tự động theo dòng tiền dư, 0 nghĩa là chủ động không đóng góp.
- `max_projection_months`: tùy chọn, tối đa 1200.

### Validation

Trả sáu khóa: `status`, `errors`, `warnings`, `missing_fields`, `clarification_questions`, `can_simulate`.

Chỉ `VALID` hoặc `WARNING` cùng `can_simulate=True` mới được chuyển sang mô phỏng. Các trạng thái còn lại chặn workflow.

### Scenario và report

- Scenario dùng `conservative`, `base`, `optimistic`, `metadata`.
- Trang scenario tích hợp tự tính lại sau khi dữ liệu đã được xác nhận ở Bước 2; giao diện demo độc lập vẫn yêu cầu xác nhận giả định mẫu.
- `app.py` lấy assumptions cuối từ kịch bản `base`, chạy lại `validate_profile`, rồi mới chuyển dữ liệu sang Người 5.
- Calculation result cho báo cáo lấy từ `scenarios.base.calculation_result` để tránh ghép số cũ.
- Báo cáo cần đủ `profile_confirmed`, `assumptions_confirmed`, `report_confirmed`.

## Quyết định tích hợp

1. Dùng Người 1 làm nguồn schema duy nhất.
2. Dùng Người 2 FIXED làm nguồn công thức duy nhất.
3. Người 3 điều khiển assumptions cuối, what-if và stress test.
4. Người 4 validation lại assumptions cuối sau trang Người 3.
5. Người 5 chỉ nhận kết quả đã xác nhận và cùng một baseline hiện hành.
6. Mọi thay đổi profile xóa review, scenario và report cũ. Mọi thay đổi scenario xóa report cũ.
7. Không có API key vẫn dùng form hoặc fixture ngoại tuyến; không giả vờ đó là kết quả LLM thật.

## Việc chưa được tuyên bố hoàn thành

- Chưa đo accuracy/groundedness của API LLM thật nếu nhóm chưa cấu hình key.
- Chưa thực hiện user study 5-10 người.
- Dashboard và báo cáo đã có lớp trình bày hoàn chỉnh; kiểm tra responsive thủ
  công trên các trình duyệt mục tiêu vẫn là bước nghiệm thu cuối tại máy nhóm.
