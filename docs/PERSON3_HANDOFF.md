# Project 09 — Bàn giao Người 3

Phạm vi: scenarios, what-if, stress test, bảng so sánh và biểu đồ. Không triển khai
extraction, business validation, LLM explanation, report generator hoặc app.py.

## 1. Sáu file để ghép vào project chung

| File | Chức năng |
|---|---|
| config/scenario_defaults.json | Giả định định lượng và giới hạn mô phỏng |
| src/scenarios.py | build_scenarios, run_what_if và điều phối engine |
| src/stress_test.py | run_stress_test, lịch thu nhập/đóng góp và phương án phục hồi |
| src/charts.py | Bảng so sánh, biểu đồ đường, biểu đồ cột |
| tests/test_scenarios.py | 59 test, gồm test tương tác Streamlit |
| ui/scenario_page.py | Giao diện tối thiểu, chạy độc lập hoặc được app chung gọi |

Tài liệu hỗ trợ: PERSON3_REQUIREMENTS.txt, tài liệu này, PERSON3_DEMO_NOTES.md.
Các kết quả mẫu và bằng chứng test nằm ở evidence/ trong gói tổng.

## 2. Dependency và nguồn mã gốc

- `src/schemas.py`: giữ nguyên từ ZIP Người 1.
- `src/calculations.py`: giữ nguyên từ thư mục `Project_09_Person_2_FIXED` trong ZIP Người 2 gửi riêng.
- Không dùng bản calculation engine cũ đi kèm ZIP Người 1.
- `parse_financial_profile(...).to_profile_dict()` chuẩn hóa đúng 15 khóa của Người 1.
- Chỉ gọi API công khai `calculate_financial_metrics(profile, assumptions)` của Người 2.
- Không copy công thức FV, công thức giải ngược PMT hoặc hàm private của Người 2 vào code sản phẩm.
- Công thức độc lập trong file TEST chỉ là oracle để đối chiếu, không được module sản phẩm import.
- `demo/` có sẵn các dependency gốc để chạy thử. Danh tính byte được kiểm tra trong `evidence/REFERENCE_CHECKSUMS.json`.

Không copy toàn bộ thư mục demo vào project nhóm để tránh chồng file. Khi bàn giao,
chỉ ghép 6 file Người 3 ở mục 1, và bảo đảm nhóm đang dùng đúng engine FIXED.

## 3. Chạy nhanh

Khuyến nghị Python 3.12, môi trường ảo riêng. Từ thư mục `demo/`:

```bash
python -m pip install -r ../person3/PERSON3_REQUIREMENTS.txt
python -m pytest -q tests/test_scenarios.py
python -m streamlit run ui/scenario_page.py
```

Chạy cả test Người 2 để đối chiếu:

```bash
python -m pytest -q tests/test_scenarios.py tests/test_calculations.py tests/test_cashflow_ui.py
```

Đối với project chung đã ghép file, cài dependencies tương thích và chạy từ thư mục
gốc project để import `src` hoạt động. Backend chỉ cần Pydantic; bảng/biểu đồ/UI mới
dùng pandas, Plotly và Streamlit. Pytest dùng cho kiểm thử.

## 4. Hợp đồng dữ liệu

- FinancialProfile có đúng 15 khóa; không thêm trường kịch bản vào schema.
- Tiền nội bộ dùng số VND; chỉ thêm dấu phân cách khi hiển thị.
- Rate là số thập phân theo năm: 0.05 = 5%/năm.
- Chuyển năm sang tháng do engine Người 2 thực hiện theo annual effective rate.
- `goal_horizon_months` là số nguyên 1–120.
- Dữ liệu hồ sơ thiếu giữ None, không tự điền 0.
- `risk_tolerance` và `liquidity_need`: low, medium, high.
- `expected_income_growth` được giữ nguyên trong profile nhưng chưa áp dụng trong MVP. Mỗi kết quả ghi rõ giới hạn này.
- Quỹ dự phòng được giữ riêng. `emergency_fund_available = min(current_savings, emergency_fund_reserved)` mô tả phần thực có.

Assumptions gửi vào module gồm đúng các tên Người 2:

| Khóa | Ý nghĩa |
|---|---|
| annual_return_rate | Bắt buộc, lợi suất giả định theo năm |
| monthly_contribution | Tùy chọn; bỏ qua hoặc None = tự động theo dòng tiền dư, 0 = chủ động đóng 0 |
| annual_inflation_rate | Tùy chọn, mặc định 0 |
| max_projection_months | Tùy chọn, mặc định 1200; từ thời hạn mục tiêu đến 1200 |

None của `monthly_contribution` là lựa chọn chế độ tự động theo API Người 2;
không phải tự lấp một trường FinancialProfile chưa được khai báo.

## 5. Ba kịch bản

| Giả định | Thận trọng | Cơ sở | Tích cực |
|---|---:|---:|---:|
| Thu nhập chính và phụ so với hồ sơ | ×0.95 | ×1.00 | ×1.05 |
| Chi phí không thiết yếu | ×1.05 | ×1.00 | ×0.95 |
| Đóng góp khi nhập số tiền riêng | ×0.90 | ×1.00 | ×1.10 |
| Đóng góp ở chế độ tự động | 90% dòng tiền dư mới | Theo engine gốc | 100% dòng tiền dư mới |
| Lợi suất so với cơ sở | −1 điểm phần trăm/năm | Không đổi | +1 điểm phần trăm/năm |

Chi phí thiết yếu, trả nợ, quỹ dự phòng, mục tiêu và thời hạn giữ nguyên trong
ba kịch bản. Mức thu nhập/chi phí đã điều chỉnh là mức cố định mỗi tháng; không
phải tăng trưởng lũy tiến. Kịch bản cơ sở giữ đúng kết quả engine gọi trực tiếp.

Giới hạn thiết kế của bài tập: lợi suất thấp nhất −5%/năm; cao nhất lần lượt
6%, 8%, 10% cho low/medium/high; lạm phát 0–15%/năm. Đây là các mức giới hạn
mô phỏng được chọn cho module, không phải dữ liệu thị trường hay ngưỡng rủi ro
được xác nhận bởi một tổ chức tài chính. Nhóm có thể thống nhất lại trong config.
Không dùng cấu hình này thay module validation của Người 4.

Lợi suất cơ sở ngoài giới hạn sẽ báo lỗi có kiểm soát. Lợi suất kịch bản sau khi
cộng offset vượt giới hạn được chặn tại biên và có cảnh báo; đồng thời lưu cả
`requested_annual_return_rate` và lợi suất thực áp dụng. Không âm thầm sửa hồ sơ gốc.

## 6. API Người 3

### build_scenarios(profile: dict, base_assumptions: dict) -> dict

Trả `conservative`, `base`, `optimistic`, `metadata`.
Mỗi kịch bản gồm:

- `scenario_name`, `label`;
- `profile_used`, `assumptions`, `scenario_adjustments`;
- `calculation_result`: nguyên tên khóa/kết quả từ engine;
- `monthly_projection`: month, balance, target_amount, monthly_contribution, cumulative_contributions;
- `total_contributions`, `investment_gain`;
- `emergency_fund_reserved`, `emergency_fund_available`, `warnings`.

Tháng 0 có số tiền khả dụng ban đầu; tháng 1 là sau lần đóng góp cuối tháng đầu tiên.
Biểu đồ lấy mỗi balance/target từ một lần gọi engine cho số tháng tương ứng.
`investment_gain` có thể âm khi lợi suất giả định âm.

### run_what_if(profile, base_assumptions, profile_updates=None, assumption_updates=None) -> dict

Trả `baseline`, `modified`, `changes`, `comparison`, `is_final_plan=False`.
Cho thay các trường thu nhập, chi phí, trả nợ, goal_amount, goal_horizon_months
và 4 assumptions của engine. Khóa không được hỗ trợ sẽ báo lỗi, không bị bỏ qua.

Nếu có monthly_contribution nhập riêng, thay thu nhập không tự đổi số đóng góp:
engine giữ cảnh báo affordability. Nếu muốn đóng theo dòng tiền mới, gửi
`assumption_updates={"monthly_contribution": None}`.

`fv_total_change`, `goal_gap_change`, `month_to_goal_change` = sau − trước.
`horizons_differ=True` nghĩa là hai số cuối kỳ được tính ở thời hạn khác nhau.

### run_stress_test(profile: dict, base_assumptions: dict, stress_config: dict) -> dict

`stress_config={}` chọn giảm cả hai nguồn thu nhập 20% trong tháng 1–3.
Các khóa: `income_reduction_rate`, `start_month`, `duration_months`.
Sau đợt stress, thu nhập và kế hoạch đóng góp trở về mức gốc.

Trong tháng bị ảnh hưởng:

1. Tạo bản sao hồ sơ với thu nhập đã giảm.
2. Gọi engine lấy khả năng đóng góp theo dòng tiền.
3. Khoản đóng góp thực mô phỏng = min(kế hoạch, khả năng đóng góp).
4. Gọi engine cho 1 tháng để chuyển số dư và mục tiêu lạm phát sang tháng tiếp theo.

Chi phí và nợ không đổi. Nếu phần dòng tiền dư chưa phân bổ đủ hấp thụ cú sốc,
đóng góp có thể không giảm; vì vậy không mặc định tiền tiết kiệm cũng giảm 20%.

Trả `baseline`, `stressed`, `comparison`, `stress_config`, `metadata`.
`stressed.monthly_projection` có thêm thu nhập, surplus, deficit, affordability gap
và cờ stress_active của từng tháng. Chuỗi hiển thị dừng ở thời hạn mục tiêu; tìm
tháng đạt mục tiêu có thể tiếp tục đến max_projection_months.

Trong `stressed.calculation_result`, `monthly_contribution` và
`required_monthly_contribution` là None vì lịch đóng góp thay đổi. Không gán một
PMT cố định gây hiểu nhầm. Đọc `planned_monthly_contribution` và chuỗi tháng để
biết đóng góp; đọc nhóm recovery trong comparison để biết phương án phục hồi.
Không giả định dictionary stress có toàn bộ chỉ tiêu dòng tiền cố định của engine.

| Chỉ tiêu comparison | Ý nghĩa |
|---|---|
| fv_total_reduction | Tiền cuối kỳ baseline trừ stressed |
| goal_gap_increase | Goal gap stressed trừ baseline |
| goal_delay_months | Tháng đạt sau stress trừ tháng đạt baseline, không âm |
| extension_months_from_original_horizon | Số tháng cần kéo dài so với thời hạn ban đầu |
| recovery_start_month | Tháng đầu tiên sau đợt stress |
| recovery_required_monthly_contribution | Khoản đóng góp cố định cần có từ recovery_start_month đến hạn gốc |
| additional_monthly_contribution_after_stress | Phần tăng thêm so với kế hoạch gốc |
| recovery_required_contribution_gap | Phần recovery PMT vượt khả năng dòng tiền sau stress |
| unfunded_cashflow_deficit | Tổng chi phí sinh hoạt còn thiếu nguồn tài trợ trong thời hạn |

Recovery được giải bằng engine với số dư cuối stress và mục tiêu đã điều chỉnh
lạm phát đến hạn gốc; không áp lạm phát hai lần. Nếu không còn tháng phục hồi
trước hạn, các chỉ tiêu recovery là None, có lý do cụ thể.

Khi lịch đóng góp không thay đổi, kết quả được đồng nhất với baseline của Người 2
để sai số số thực khi cộng dồn theo tháng không đảo trạng thái đạt mục tiêu.

### API biểu đồ

- `build_comparison_table(result)` → pandas DataFrame: chỉ tiêu theo hàng, kịch bản theo cột.
- `create_balance_chart(result)` → Plotly Figure.
- `create_final_value_chart(result)` → Plotly Figure.

Nhận kết quả của cả ba API trên hoặc mock cùng cấu trúc. Không gọi engine.
Mỗi kịch bản có đường mục tiêu riêng, kể cả khi what-if đổi thời hạn/lạm phát.
Kiểm tra điểm cuối khớp fv_total trước khi vẽ; không sửa số để làm khớp.

## 7. Tích hợp giao diện và Người 4/5

```python
from ui.scenario_page import render_scenario_page

# Lời gọi minh họa cho người tích hợp; Người 3 không sửa app.py.
result = render_scenario_page(
    profile,
    assumptions,
    validation_status=validation_result["status"],
    profile_confirmed=profile_confirmed,
)
```

`VALID` hoặc `WARNING` cộng hồ sơ đã xác nhận mới mở giao diện mô phỏng thực.
Các trạng thái khác trả None. Tên biến ở app.py do nhóm ghép sau; không giả định
một session-state key của Người 4 chưa được bàn giao. Truyền cờ xác nhận thật.

UI yêu cầu xác nhận assumptions. Khi rate/inflation thay đổi hoặc hồ sơ thay đổi,
xác nhận cũ bị hủy. What-if và stress chỉ là bản mô phỏng. Reset xóa state có tiền
tố person3_, không xóa dữ liệu của thành viên khác. Hàm trả None khi chưa xác nhận
hoặc gặp lỗi; caller không được dùng kết quả cũ để tạo báo cáo cuối.

Kết quả giao diện có `scenarios`, `what_if`, `stress_test`, `is_final_plan=False`.
Khi ghép với Người 5, truyền các phần này trong dictionary kết quả đã thống nhất,
không đổi chữ ký generate_explanation. Người 5 cần đọc được lịch đóng góp biến
đổi, None timing/PMT và cảnh báo affordability; không tự tạo con số bị thiếu.

Mọi lỗi dự kiến ở API module được bọc bằng ScenarioInputError; UI hiển thị lỗi và
trả None. Module không triển khai lại các trạng thái nghiệp vụ của Người 4.

## 8. Kiểm thử và kết quả

- 59 test Người 3: hợp đồng, bất biến, ba kịch bản, what-if, stress, recovery,
  lợi suất/lạm phát, trường hợp biên, sai số tại đúng mục tiêu, mock charts và UI.
- 19 test gốc Người 2: 18 backend + 1 Streamlit UI, giữ nguyên mã test.
- Tổng: **78 passed, 0 failed, 0 skipped**.
- `python -m compileall -q src ui tests`: đạt.
- Smoke chạy trực tiếp ui/scenario_page.py: không exception, 6 biểu đồ; đổi hồ sơ
  làm mất xác nhận cũ; Reset và cập nhật what-if được AppTest kiểm chứng.

Đây là kiểm thử module Người 3 với dependency Người 1/2, không phải integration
test toàn bộ 5 thành viên. Chưa tích hợp LLM, API, review_page hoặc report_page.
Không tuyên bố đã chạy lại/recalculate file Excel của Người 2 trong lượt này.

## 9. Giới hạn cần nói rõ khi bàn giao

- Chưa mô hình hóa nguồn bù dòng tiền sinh hoạt âm. Có cảnh báo/định lượng thiếu hụt;
  không tự rút quỹ dự phòng hoặc trừ tiền mục tiêu. Số dư lúc này là dự phóng có điều kiện.
- Chưa áp dụng tăng trưởng thu nhập lũy tiến, thuế, phí hoặc biến động ngẫu nhiên.
- Không có xác suất thành công; chỉ có trạng thái theo giả định.
- `estimated_month_to_goal=None` nghĩa là chưa đạt trong giới hạn dự phóng.
- Thời hạn nhập 1–120 tháng; giới hạn tìm tháng đạt tối đa 1200 không phải thời hạn
  người dùng được phép nhập. Đây là cùng quy ước engine Người 2.
- Giao diện demo chỉ dùng P001, P006, P019 giả lập. Không được bật demo_mode cho
  hồ sơ thực để bỏ qua validation.
- Chưa trang trí dashboard hoặc ghép app.py; thực hiện sau integration test cả nhóm.
