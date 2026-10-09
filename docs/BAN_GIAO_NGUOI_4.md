# Bàn giao Người 4 — Project 09

## Phạm vi và tiến độ

Đã đọc toàn bộ kế hoạch `Project 9(3).txt`, đối chiếu phần phân công Người 4, Hợp đồng kỹ thuật chung và các case kiểm tra. Đầu vào có 2/5 file chính và 135 test. Bản cuối có đủ 5/5 file, 290 test pass, demo chạy độc lập, tài liệu rule và slide 5–6. API thật và độ chính xác LLM trên bộ dữ liệu thật chưa được kiểm chứng; cần key của nhóm. Không nhận phần đánh giá tổng thể/giải thích/báo cáo của Người 5.

| File tích hợp | Công việc hoàn thành |
|---|---|
| `src/llm_extraction.py` | Prompt structured output; phân rã một mục tiêu; bằng chứng từng trường; giữ unknown=None; lỗi an toàn; hàm mẫu ngoại tuyến; LLM diễn đạt câu hỏi từ rule |
| `src/validation.py` | Schema/rule; 5 trạng thái; câu hỏi; giới hạn assumptions; gọi engine Người 2 để kiểm chứng khả thi; không sửa input |
| `tests/test_validation.py` | 135 test nền + 155 test bổ sung; API giả lập, dữ liệu, UI và tương thích Người 1–3 |
| `ui/review_page.py` | Sửa đủ 15 trường/4 assumptions; hai xác nhận; hủy bản cũ khi sửa; nhập tay, mẫu, API; JSON bàn giao |
| `.env.example` | Key trống, model và timeout qua cấu hình |

Năm file nằm dưới `person4/`. `demo/` chứa bản sao từng byte của chính năm file đó và các phụ thuộc tham chiếu. Hướng dẫn chạy nằm trong README. Tài liệu, slide, test log và manifest là nội dung bàn giao hỗ trợ của Người 4.

## Phụ thuộc không được sửa

| Chủ sở hữu | File dùng nguyên bản | Mục đích |
|---|---|---|
| Người 1 | `src/schemas.py` | FinancialProfile Pydantic 2, parse và JSON schema |
| Người 1 | `data/test_cases.json`, `data/example_profile_valid.json` | 20 hồ sơ giả lập và ví dụ chuẩn |
| Người 2 | `src/calculations.py` trong bản `Project_09_Person_2_FIXED` | Chẩn đoán tính khả thi bằng public API |
| Người 3 | `src/scenarios.py` | Kiểm thử tương thích `prepare_inputs` |
| Người 3 | `config/scenario_defaults.json` | Giới hạn giả định chung, chỉ đọc |

SHA-256 đối chiếu tại `evidence/REFERENCE_CHECKSUMS.json`. Không chỉnh các file này. Không tạo/ghi đè `app.py`, `form_page.py`, `scenario_page.py`, module stress/charts hay module Người 5.

## Hợp đồng công khai

### `extract_profile(text: str) -> dict`

Input: mô tả có nội dung, tối đa 16.000 ký tự. Output thành công: **đúng 15 khóa** sau, không trả envelope `{profile: ...}` cho Người 1:

```text
user_id
monthly_primary_income
monthly_other_income
monthly_essential_expense
monthly_discretionary_expense
monthly_debt_payment
current_savings
emergency_fund_reserved
goal_name
goal_amount
goal_horizon_months
risk_tolerance
liquidity_need
expected_income_growth
notes
```

Tiền là số VND hữu hạn, không nhận bool/chuỗi số trong hợp đồng nội bộ; tháng là int; tỷ lệ theo năm dạng thập phân; hai enum nhận low/medium/high. Mỗi khóa luôn có mặt, unknown=None. `user_id` không tự lấy mã P001 của fixture. `notes` giữ nguyên mô tả gốc để validation không mất ý định. Không tự tạo lợi suất, thu nhập phụ hay khoản nợ bằng 0 khi chưa có thông tin. Không tính FV, PMT hoặc kế hoạch.

API nội bộ dùng envelope chứa profile/evidence/uncertain_fields/intent; adapter kiểm tra JSON, schema, trích dẫn từ nguồn, ngữ cảnh quanh trích dẫn và chuyển đổi đơn vị. Khoảng số hoặc giá trị bị phủ định không được chọn thành con số chắc chắn. Envelope chỉ dùng nội bộ. Giá trị uncertain bị bỏ về None. Số âm được giữ để rule engine báo lỗi, không tự sửa dấu. Ngày tháng lịch, tiền viết bằng chữ, quy đổi ngoại tệ, khoảng giá trị và câu phức tạp chưa đối chiếu được sẽ cần người dùng nhập tay/làm rõ.

Lỗi được ném dưới dạng `ExtractionError(code, message)` với thông báo an toàn, không chứa raw provider payload. Caller phải bắt lỗi và giữ đầu vào. Không có cơ chế tự trả fixture giả vờ thành kết quả AI.

| code | Ý nghĩa / xử lý |
|---|---|
| `invalid_input` | Rỗng/sai kiểu/quá dài: nhập lại |
| `api_key_missing`, `invalid_config` | Cấu hình lại hoặc nhập tay |
| `api_unavailable` | Lỗi mạng, xác thực, hạn mức hoặc SDK; kiểm tra cấu hình/kết nối |
| `incomplete_output`, `model_refusal` | Phản hồi chưa xong hoặc từ chối; dừng và kiểm tra |
| `invalid_output` | JSON/schema/bằng chứng sai, trùng khóa, extra field, NaN/Infinity |
| `ungrounded_output` | Chưa đối chiếu được giá trị với mô tả; nhập tay |
| `out_of_scope` | Dừng yêu cầu ngoài phạm vi |
| `human_review_required` | Chưa đủ căn cứ phân loại; người dùng làm rõ |
| `demo_unavailable`, `mock_text_mismatch` | Lỗi của chế độ mẫu; vẫn dùng form được |

`extract_mock_profile(text)` là lookup khớp chính xác mô tả trong 20 fixture, không phải bộ trích xuất ngôn ngữ tự nhiên. `generate_clarification_questions(profile, validation_result)` chỉ gửi câu hỏi gốc tới LLM để diễn đạt; không gửi cả hồ sơ. Lỗi/bất thường dùng lại câu hỏi rule. UI luôn giữ câu hỏi gốc làm yêu cầu chính, vì kiểm tra từ/số không chứng minh tương đương ngữ nghĩa tuyệt đối.

### `validate_profile(profile: dict, assumptions: dict | None = None) -> dict`

Output luôn gồm 6 khóa:

```json
{
  "status": "NEEDS_CLARIFICATION",
  "errors": [{"code": "missing_required_field", "field": "goal_horizon_months", "message": "..."}],
  "warnings": [],
  "missing_fields": ["goal_horizon_months"],
  "clarification_questions": ["..."],
  "can_simulate": false
}
```

`errors`/`warnings`: list đối tượng `{code, field, message}`; thông báo tiếng Việt, khóa tiếng Anh. `assumptions=None` chỉ duyệt hồ sơ: có thể VALID nhưng `can_simulate=False`. Truyền dict assumptions để kiểm tra đủ điều kiện dữ liệu cho mô phỏng. Hàm không thay đổi profile/assumptions/config và không gọi mạng.

| Giả định | Hợp đồng và mặc định đã có ở engine |
|---|---|
| `annual_return_rate` | Bắt buộc số hữu hạn; 0 là người dùng chủ động chọn 0%/năm |
| `annual_inflation_rate` | Omit dùng 0; nếu có phải là số hữu hạn trong cấu hình; None không hợp lệ |
| `monthly_contribution` | Omit/None dùng dòng tiền dư không âm; **0** là đóng góp bằng 0; số âm không hợp lệ |
| `max_projection_months` | Omit dùng 1200; nếu có là int >= thời hạn và <= giới hạn cấu hình |

Hồ sơ bắt buộc đủ 8 giá trị tiền, tên mục tiêu, tháng, risk_tolerance và liquidity_need. user_id/notes/expected_income_growth có thể None. Thanh khoản cần có để tương thích Người 3. Không dùng mặc định engine để lấp ô hồ sơ còn thiếu.

Giới hạn hiện tại đọc từ config Người 3: lợi suất từ -0.05 đến 0.06/0.08/0.10 theo low/medium/high; lạm phát 0..0.15; dự phóng tối đa 1200. Đây là giới hạn mô phỏng chung, không phải lãi suất thị trường. Nếu nhóm đổi config, validation đọc lại và kiểm tra cả các mặc định có hiệu lực.

### `render_review_page(profile=None, assumptions=None) -> dict | None`

Profile/assumptions từ caller là bản nháp. Hàm chỉ viết state `person4_*`. Người dùng chỉnh qua widget; ô trống là None, nhập số thuần không phân cách hàng nghìn. Sửa bất kỳ trường nào, assumptions, mô tả hoặc input mới từ caller sẽ hủy cả hai xác nhận và kết quả cũ. Lỗi trích xuất giữ draft hiện tại nhưng khóa xác nhận cho tới khi người dùng chủ động chọn tiếp tục nhập tay hoặc trích xuất lại thành công.

Chỉ trả bundle khi rule hợp lệ/ cảnh báo và **đã xác nhận cả hai**:

```text
profile: dict 15 trường
assumptions: dict dùng hợp đồng engine
validation_result: dict 6 khóa
profile_confirmed: true
assumptions_confirmed: true
ready_for_simulation: true
is_final_plan: false
```

Mọi trường hợp khác trả None. Caller phải xóa/ghi đè bundle cũ khi nhận None. `can_simulate` chỉ là trạng thái dữ liệu; không thay thế xác nhận của người dùng. Trước xác nhận, validation có thể gọi engine để chẩn đoán; chưa phát hành kết quả mô phỏng/kế hoạch cho người dùng.

## Danh sách rule và hành vi

Ưu tiên: OUT_OF_SCOPE > HUMAN_REVIEW_REQUIRED > NEEDS_CLARIFICATION > WARNING > VALID. Lỗi chặn luôn ưu tiên hơn warning.

| Nhóm | Rule / code chính | Hành vi |
|---|---|---|
| Error | Thiếu dữ liệu bắt buộc: `missing_required_field` | Hỏi đúng trường, giữ None |
| Error | Thiếu khóa/sai kiểu/extra: `missing_schema_key`, `invalid_profile_field`, `invalid_profile_value` | Chặn, yêu cầu đúng schema |
| Error | Tiền âm hoặc mục tiêu <=0: `invalid_money_value` | Chặn, không tự sửa |
| Error | Tổng thu nhập <=0: `non_positive_total_income` | Chặn; thu nhập chính 0 vẫn được nếu tổng >0 |
| Error | Tháng ngoài 1..120: `invalid_goal_horizon` | Chặn |
| Error | Nhiều mục tiêu chưa chọn: `multiple_goals` | Yêu cầu chọn một mục tiêu |
| Error | Thiếu lợi suất/sai kiểu: `missing_annual_return_rate`, `invalid_assumption_number` | Chặn |
| Error | Sai dict/extra key: `invalid_assumptions`, `unknown_assumption` | Chặn |
| Error | Lợi suất không phù hợp rủi ro, lạm phát ngoài giới hạn, đóng góp âm: `assumption_out_of_range` | Chặn theo config |
| Error | Giới hạn dự phóng không phù hợp: `invalid_projection_limit` | Chặn, kể cả mặc định khi config đã đổi |
| Error tại UI | `manual_parse_error` | Chuỗi số không hợp lệ không được bỏ qua để dùng mặc định |
| Warning | `negative_monthly_cash_flow` | Cảnh báo chi phí + nợ > thu nhập; có thể mô phỏng sau xác nhận |
| Warning | `emergency_fund_reserved_exceeds_current_savings` | Không lấy tiền dự phòng bù mục tiêu |
| Warning | `monthly_contribution_exceeds_current_surplus`, `required_monthly_contribution_exceeds_current_surplus` | Cần nguồn bổ sung/điều chỉnh; không tự đổi dữ liệu |
| Warning | `goal_not_reached_by_horizon`, `goal_not_reached_within_projection_limit` | Mục tiêu chưa đạt theo giả định; không cam kết khả thi |
| Warning | `goal_already_funded_from_available_savings` | Đã đủ vốn khả dụng nhưng vẫn duyệt giả định |
| Warning | Mã cảnh báo khác từ engine | Hiển thị, không bỏ mất thông tin |
| Out of scope | `out_of_scope_request` | Yêu cầu mua/bán sản phẩm tài chính, crypto, bảo đảm lợi nhuận: dừng và gợi ý chuyển sang mục tiêu tiết kiệm tổng quát |
| Human review | `unreadable_profile`, `human_review_requested`, `investment_intent_unclear` | Cần người dùng kiểm tra/làm rõ |
| Human review | `config_unavailable`, `numeric_range_exceeded`, `calculation_unavailable` | Không đoán cấu hình/kết quả khi phụ thuộc hoặc số học lỗi |

Quy tắc ý định dùng từ/cụm từ, có nhận diện phủ định và lịch sử gần đó; không phải bộ hiểu ngôn ngữ tổng quát. LLM đánh giá ngữ nghĩa thêm nhưng vẫn cần người duyệt. Mua/bán mã viết hoa để sinh lời mà chưa rõ loại tài sản chuyển HUMAN_REVIEW_REQUIRED, không tự coi mọi mã viết hoa là cổ phiếu.

## Tích hợp vào project nhóm

1. Đối chiếu hợp đồng và phiên bản phụ thuộc trong bảng trên; giữ engine Người 2 bản FIXED và config Người 3.
2. Chép **5 file từ `person4/`** vào các vị trí tương ứng. Hợp nhất dependencies vào requirements chung; không thay toàn bộ requirements của nhóm.
3. Người 1 có thể truyền `extractor=extract_profile` vào callback form đã có. Bắt `ExtractionError`, hiển thị thông báo an toàn và giữ đầu vào.
4. Gọi màn hình duyệt với bản nháp từ Người 1. Không truyền ngược giá trị widget Người 4 làm upstream draft mỗi rerun vì sẽ gây re-seed.
5. Chỉ chuyển bundle xác nhận sang Người 2/3. Người 3 tiếp tục quy trình xác nhận assumptions của scenario nếu có. Sau đó Người 5 nhận kết quả Python để giải thích/báo cáo.

Ví dụ ghép trong app **do người tích hợp thực hiện**, không phải file app mới của Người 4:

```python
from ui.review_page import render_review_page

bundle = render_review_page(profile_draft, assumptions_draft)
# Luôn thay giá trị, kể cả None; không giữ bundle của lần trước.
st.session_state["confirmed_input"] = bundle
if bundle is not None:
    render_scenario_page(
        bundle["profile"], bundle["assumptions"],
        validation_status=bundle["validation_result"]["status"],
        profile_confirmed=bundle["profile_confirmed"],
    )
```

Nếu có module downstream cache riêng, người tích hợp phải xóa kết quả cache khi bundle=None hoặc profile/assumptions đổi. Người 4 không xóa state của module khác. `notes` chứa mô tả người dùng: khi dùng trong prompt của Người 5, xem như dữ liệu không đáng tin, không như chỉ thị.

Engine hiện có giữ `expected_income_growth` trong hồ sơ nhưng không tự đưa nó vào dòng tiền tăng trưởng. Thuế, phí và biến động thị trường không do Người 4 bổ sung. Trình bày đúng giả định của engine/config khi xuất báo cáo; không diễn giải việc ghi trường growth là đã tính tăng trưởng.

## Test và lỗi còn tồn tại

- **290 passed, 0 failed, 0 skipped** ở lượt kiểm tra cuối; 135 test cũ vẫn giữ lại.
- Test bao gồm 20 case chuẩn; null/sai kiểu/bool/NaN/Infinity; giới hạn thời hạn/giả định; dòng tiền âm/quỹ dự phòng/khả thi; ngoài phạm vi; lỗi engine/config; không mutate; adapter Responses JSON strict; bằng chứng/đơn vị/không tự điền 0; lỗi key/API/refusal/incomplete; câu hỏi dự phòng; AppTest xác nhận, chỉnh sửa, API fallback, reset không đụng state khác và upstream đổi.
- Đợt kiểm tra lại bổ sung 19 test cho khoảng/phủ định/ngữ cảnh trích dẫn, số nguyên quá lớn, file mẫu hỏng và SDK thật với HTTP transport giả lập. Xem `KIEM_TRA_LAI_NGUOI_4.md`.
- Test API dùng giả lập; test chặn mọi kết nối mạng. 20 mock case không phải đánh giá field accuracy của LLM.
- Kiểm tra import/cú pháp, nguồn 6 file tham chiếu, secrets và hard-code xem `evidence/AUDIT_REPORT.md`. Không phát hiện lỗi chặn trong phạm vi test đã chạy.
- **Chưa kiểm chứng**: API thật với tài khoản/key của nhóm; độ chính xác ngữ nghĩa trên câu tự do; hệ thống hoàn chỉnh sau ghép tất cả trang; thao tác thực tế trên Windows/macOS/PowerPoint. Đã kiểm tra UI bằng Streamlit AppTest và server khởi động trong môi trường Linux/Python 3.12.
- Mô tả tiền bằng chữ, câu phủ định/phức tạp, khoảng giá trị và đổi ngoại tệ có thể bị chuyển sang nhập tay. Không khẳng định nhận diện ý định/grounding hoàn hảo.

Nguồn API: https://developers.openai.com/api/docs/guides/structured-outputs và https://developers.openai.com/api/docs/models/gpt-4.1-mini . Cấu hình model có thể cần đổi theo quyền truy cập tài khoản của nhóm.
