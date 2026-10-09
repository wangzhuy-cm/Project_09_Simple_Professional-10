# Project 09 — Bàn giao Người số 2 (Financial Calculation Engine)

## 1. Phạm vi

Người 2 chỉ phụ trách Financial Calculation Engine và giao diện cash-flow tối thiểu. Không sửa module của Người 1, 3, 4 hoặc 5.

## 2. File Người 2 bàn giao

- `src/calculations.py`
- `tests/test_calculations.py`
- `tests/test_cashflow_ui.py`
- `ui/cashflow_page.py`
- `outputs/person2_formula_verification.xlsx`
- `PERSON2_HANDOFF.md`
- `PERSON2_TEST_RESULTS.txt`

## 3. Contract chính

```python
calculate_financial_metrics(profile: dict, assumptions: dict) -> dict
```

### Input `profile`

Dùng dictionary theo FinancialProfile schema 15 khóa của Người 1. Engine cần các trường số sau không phải `None`:

- `monthly_primary_income`
- `monthly_other_income`
- `monthly_essential_expense`
- `monthly_discretionary_expense`
- `monthly_debt_payment`
- `current_savings`
- `emergency_fund_reserved`
- `goal_amount`
- `goal_horizon_months`

### Input `assumptions`

- `annual_return_rate`: **bắt buộc**, decimal theo năm.
- `monthly_contribution`: tùy chọn. Nếu bỏ trống, engine dùng `max(monthly_surplus, 0)`.
- `annual_inflation_rate`: tùy chọn, mặc định `0.0`.
- `max_projection_months`: tùy chọn, mặc định `max(goal_horizon_months, 1200)`.

### Quy tắc rate

Annual effective rate -> monthly effective rate:

```text
monthly_rate = (1 + annual_rate)^(1/12) - 1
```

## 4. Contract tích hợp validation — BẮT BUỘC

`calculate_financial_metrics()` **không thay thế module validation của Người 4**. Hàm này giả định profile đã đi qua validation và user confirmation trước khi được dùng để tạo kế hoạch cuối cùng.

Workflow khi tích hợp phải là:

```text
Extraction
→ Validation
→ User confirmation
→ Calculation
→ Scenarios / Stress test
→ Explanation / Report
```

Không được để giao diện tạo kế hoạch cuối bằng cách gọi trực tiếp calculation engine trên một profile chưa được validation. Việc engine có thể tính được một profile thiếu trường không tham gia công thức (ví dụ `risk_tolerance`) không có nghĩa profile đó hợp lệ cho workflow cuối.

## 5. Công thức chính

```text
Total income = primary income + other income
Total outflow = essential expense + discretionary expense + debt payment
Monthly surplus = total income - total outflow
Savings rate = monthly surplus / total income
Initial available = max(current savings - emergency fund reserved, 0)
FV_initial = PV * (1 + i)^n
FV_contribution = PMT * (((1 + i)^n - 1) / i)
If i = 0: FV_contribution = PMT * n
FV_total = FV_initial + FV_contribution
Goal gap = adjusted goal amount - FV_total
```

Khoản PMT cần thiết được giải ngược từ công thức niên kim. Tháng đạt mục tiêu được mô phỏng theo tháng với đóng góp vào cuối tháng.

## 6. Affordability indicators mới

Engine không tự chặn một assumption chỉ vì khoản đóng góp lớn hơn dòng tiền hiện tại, vì Người 3 vẫn cần chạy what-if/scenario. Thay vào đó engine trả thêm chỉ tiêu và warning:

```text
affordable_monthly_contribution = max(monthly_surplus, 0)
contribution_affordability_gap = max(monthly_contribution - affordable_monthly_contribution, 0)
required_contribution_gap = max(required_monthly_contribution - affordable_monthly_contribution, 0)
```

Nếu `contribution_affordability_gap > 0`:

```text
monthly_contribution_exceeds_current_surplus
```

Nếu `required_contribution_gap > 0`:

```text
required_monthly_contribution_exceeds_current_surplus
```

Hai output này giúp Người 3 và Người 5 phân biệt giữa “kết quả toán học của scenario” và “khả năng chi trả theo dòng tiền hiện tại”.

## 7. Assumptions MVP

- Dòng tiền theo tháng.
- Đóng góp vào cuối tháng.
- Lợi suất cố định trong một lần tính.
- Chưa tính thuế và phí.
- Inflation là tùy chọn và mặc định tắt.
- `expected_income_growth` không tự áp vào engine lõi; Người 3 dùng trường này khi xây scenario/what-if nếu cần.

## 8. Edge cases đã xử lý

- Lợi suất bằng 0.
- Lợi suất khác 0.
- Thời hạn 1 tháng.
- Dòng tiền âm.
- Mục tiêu đã đủ vốn từ đầu.
- Quỹ dự phòng lớn hơn current savings.
- Tổng thu nhập bằng 0 (`savings_rate = None`).
- Thiếu field cần tính hoặc thiếu annual return assumption.
- Monthly contribution vượt monthly surplus.
- Required contribution vượt monthly surplus.
- Không mutate profile/assumptions đầu vào.

## 9. Output chính

Kết quả là dictionary với English keys, gồm:

- `total_monthly_income`
- `total_monthly_outflow`
- `monthly_surplus`
- `savings_rate`
- `initial_available_amount`
- `monthly_contribution`
- `contribution_source`
- `affordable_monthly_contribution`
- `contribution_affordability_gap`
- `annual_return_rate`, `monthly_return_rate`
- `annual_inflation_rate`, `monthly_inflation_rate`
- `fv_initial`, `fv_contribution`, `fv_total`
- `goal_gap`, `goal_reached_by_horizon`
- `required_monthly_contribution`
- `required_contribution_gap`
- `estimated_month_to_goal`
- `calculation_warnings`
- `assumptions_used`

## 10. Excel verification

`outputs/person2_formula_verification.xlsx` hiện kiểm chứng độc lập 4 case:

1. P001 — 0% return, 36 tháng.
2. P001 — 6% annual effective return.
3. Zero return — horizon 1 tháng.
4. P001 — inflation 4%/năm.

Mỗi case so sánh `Excel Result` với `Python Result` và kiểm tra Difference/PASS. Cột `Calculation` mô tả rõ công thức, tránh nhầm với cột kết quả.

## 11. Chạy test

Từ thư mục gốc của gói Người 2:

```bash
python -m pytest -q tests/test_calculations.py tests/test_cashflow_ui.py
python -m compileall -q src ui tests
```

Backend test không cần Streamlit. `tests/test_cashflow_ui.py` sử dụng `streamlit.testing.v1.AppTest`; nếu môi trường chưa cài Streamlit thì pytest sẽ skip test UI thay vì báo fail.

Để chạy smoke test UI:

```bash
python -m pip install "streamlit>=1.30" pytest
python -m pytest -q tests/test_cashflow_ui.py
```

## 12. Lưu ý cho Người 3

- Gọi `calculate_financial_metrics()` cho từng assumptions/scenario; **không copy công thức** sang `scenarios.py`.
- Khi what-if/stress test thay đổi profile, luôn tạo bản copy; không mutate profile gốc.
- Có thể dùng `contribution_affordability_gap` và `required_contribution_gap` để so sánh khả năng dòng tiền giữa các scenario.
- Scenario assumptions do Người 3 quyết định; Người 2 không tự chọn mức return/contribution cho conservative/base/optimistic.

## 13. Lưu ý cho Người 5

- Có thể dùng `required_contribution_gap` để giải thích vì sao mục tiêu chưa khả thi theo cash flow hiện tại.
- Không tính lại số bằng LLM; chỉ giải thích JSON do Python cung cấp.
