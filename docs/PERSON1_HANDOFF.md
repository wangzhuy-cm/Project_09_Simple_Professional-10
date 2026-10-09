# Project 09 — Bàn giao Người số 1

## 1. Phạm vi đã hoàn thành

Người số 1 phụ trách business scope, dữ liệu giả lập, FinancialProfile schema
và giao diện nhập hồ sơ. Gói này không chứa calculation engine, validation
engine, scenarios, stress test, LLM explanation hoặc report generator.

MVP sử dụng:

- Người dùng mục tiêu: sinh viên và người mới đi làm.
- Một người dùng và một mục tiêu chính tại một thời điểm.
- Dòng tiền theo tháng, thời hạn 1–120 tháng.
- Dữ liệu hoàn toàn giả lập, không có thông tin định danh thật.
- LLM chỉ trích xuất dữ liệu; Python thực hiện tính toán.

## 2. Danh sách file

| File | Nội dung |
| --- | --- |
| `src/schemas.py` | FinancialProfile và JSON Schema dùng chung |
| `data/sample_profiles.csv` | 20 hồ sơ đầu vào có mô tả tiếng Việt và dữ liệu cấu trúc |
| `data/expected_results.csv` | Ground truth trích xuất theo 15 trường |
| `data/test_cases.json` | Manifest machine-readable của 20 test case |
| `data/example_profile_valid.json` | JSON hợp lệ dùng để tích hợp nhanh |
| `data/example_profile_missing.json` | JSON có trường thiếu được biểu diễn bằng `null` |
| `ui/profile_page.py` | Form nhập thủ công và natural-language mock mode |
| `tests/test_person1_contract.py` | Test hợp đồng FinancialProfile |
| `tests/test_person1_data_and_ui.py` | Test CSV/JSON, mock extraction và Streamlit smoke test |

## 3. Data dictionary

| Trường | Kiểu nội bộ | Đơn vị/miền giá trị | Ý nghĩa |
| --- | --- | --- | --- |
| `user_id` | `str \| None` | Mã giả lập | Không dùng CCCD hoặc tài khoản thật |
| `monthly_primary_income` | `number \| None` | VND/tháng | Thu nhập chính |
| `monthly_other_income` | `number \| None` | VND/tháng | Thu nhập phụ |
| `monthly_essential_expense` | `number \| None` | VND/tháng | Chi phí thiết yếu |
| `monthly_discretionary_expense` | `number \| None` | VND/tháng | Chi phí không thiết yếu |
| `monthly_debt_payment` | `number \| None` | VND/tháng | Khoản trả nợ |
| `current_savings` | `number \| None` | VND | Tiền tiết kiệm hiện có |
| `emergency_fund_reserved` | `number \| None` | VND | Phần tiền phải giữ làm dự phòng |
| `goal_name` | `str \| None` | Văn bản | Tên mục tiêu chính |
| `goal_amount` | `number \| None` | VND | Giá trị mục tiêu |
| `goal_horizon_months` | `int \| None` | Tháng | Thời hạn mục tiêu |
| `risk_tolerance` | `str \| None` | `low`, `medium`, `high` | Mức chấp nhận rủi ro |
| `liquidity_need` | `str \| None` | `low`, `medium`, `high` | Nhu cầu thanh khoản |
| `expected_income_growth` | `number \| None` | Tỷ lệ năm dạng thập phân | Ví dụ 5% được lưu là `0.05` |
| `notes` | `str \| None` | Văn bản | Thông tin bổ sung |

Quy ước bắt buộc:

- JSON luôn có đủ 15 khóa.
- Chưa có dữ liệu thì dùng `null`/`None`, không tự thay bằng `0`.
- `0` chỉ có nghĩa là người dùng đã khai báo giá trị bằng 0.
- Tiền nội bộ dùng số VND, không có dấu phân cách hàng nghìn.
- Schema kiểm tra cấu trúc và kiểu; `src.validation` của Người 4 kiểm tra rule
  nghiệp vụ như số âm, dòng tiền âm, thời hạn ngoài 1–120 tháng và mâu thuẫn.

## 4. Phân bổ 20 test case

| Nhóm | Số lượng | Case ID |
| --- | ---: | --- |
| Hợp lệ, khả thi | 5 | P001–P005 |
| Hợp lệ, chưa khả thi | 3 | P006–P008 |
| Thiếu thông tin | 3 | P009–P011 |
| Mâu thuẫn/không hợp lệ nghiệp vụ | 3 | P012–P014 |
| Dòng tiền âm | 2 | P015–P016 |
| Ngoài phạm vi | 2 | P017–P018 |
| Stress test | 2 | P019–P020 |

`expected_null_fields` chỉ liệt kê trường tài chính thiếu; trường `notes` là
thông tin tùy chọn nên không được tính là lỗi thiếu dữ liệu.

## 5. Hợp đồng dành cho Người số 2

Người số 2 nên nhận dictionary từ:

```python
from src.schemas import parse_financial_profile

profile = parse_financial_profile(raw_profile).to_profile_dict()
```

Đầu ra có đúng 15 khóa và không làm thay đổi `raw_profile`. Các giá trị tiền
được chuẩn hóa thành `float`; calculation engine cần chấp nhận số `int` hoặc
`float`. Không chạy calculation đối với hồ sơ có `None` ở trường bắt buộc trước
khi Người 4 trả trạng thái cho phép tính toán.

Để lấy một case hợp lệ độc lập với giao diện:

```python
import json

with open("data/test_cases.json", encoding="utf-8") as handle:
    cases = json.load(handle)["cases"]

profile = cases[0]["expected_profile"]  # P001
```

Không import `ui.profile_page` trong calculation engine. UI là lớp ngoài và có
dependency Streamlit; `src.schemas` chỉ phụ thuộc Pydantic.

## 6. Hợp đồng giao diện

```python
render_profile_page(extractor=None) -> dict | None
```

- Không truyền `extractor`: dùng exact-match mock từ `test_cases.json`.
- Khi tích hợp Người 4: truyền `extract_profile(text: str) -> dict`.
- Trang chỉ tạo `profile_draft`; xác nhận cuối thuộc `ui/review_page.py`.
- Không có API key hoặc lời gọi mạng trong module Người 1.

## 7. Cài đặt và chạy

Yêu cầu: Python 3.10+.

```bash
python -m pip install "pydantic>=2,<3" "pandas>=2" "streamlit>=1.30" pytest
python -m pytest -q
python -m compileall -q src ui tests
python -m streamlit run ui/profile_page.py
```

Kết quả kiểm thử tại thời điểm bàn giao:

```text
49 passed
```

## 8. Lưu ý tích hợp

- Chạy lệnh từ thư mục gốc `project_09` để `from src.schemas ...` hoạt động.
- Person 4 phải yêu cầu LLM trả đủ 15 khóa; trường không biết phải là `null`.
- Enum phải là đúng `low`, `medium`, `high` bằng chữ thường.
- Lợi suất/lạm phát/tăng trưởng thu nhập đều dùng tỷ lệ năm dạng thập phân;
  calculation engine chịu trách nhiệm chuyển sang tháng.
- P019 được thiết kế để đạt mục tiêu trong baseline không lợi suất nhưng hụt
  khi thu nhập giảm 20% trong 3 tháng.
- P020 được thiết kế để đạt baseline không lợi suất nhưng hụt khi chi phí tăng
  15%.
- Không sửa trực tiếp dữ liệu đầu vào; luôn tạo dictionary kết quả mới.
