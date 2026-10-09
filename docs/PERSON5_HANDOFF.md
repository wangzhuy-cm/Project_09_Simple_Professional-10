# Project 09 - Bàn giao Người 5

## 1. Phạm vi và file

Chỉ thực hiện giải thích AI, evaluation, báo cáo và giao diện kết quả theo `Project 9(3).txt`. Không sửa file Người 1-4, `app.py`, công thức tài chính, validation, kịch bản, stress hoặc biểu đồ.

| File chính thức | Vai trò |
|---|---|
| `src/llm_explanation.py` | `generate_explanation(profile, calculation_result, scenario_result, validation_result) -> str` |
| `src/evaluation.py` | Field accuracy, completeness, precision/recall/F1, numeric groundedness/hallucination screen, thời gian xử lý |
| `src/report_generator.py` | `generate_report(profile, results, explanation, output_path) -> str` |
| `tests/test_llm_outputs.py` | Test hợp đồng, chặn nội dung AI sai, PDF, UI và dữ liệu P019 |
| `ui/report_page.py` | Kiểm tra lời giải thích, xác nhận báo cáo và tải PDF |
| `outputs/evaluation_results.csv` | Kết quả đã đo và trường còn chờ đo được ghi rõ |
| `outputs/sample_report.pdf` | Báo cáo P019 giả lập, lợi suất cơ sở 0%, ở chế độ ngoại tuyến |

File hỗ trợ thuộc Người 5: `requirements-person5.txt`, tài liệu này, `PERSON5_DEMO_NOTES.md`, font Unicode trong `assets/` kèm giấy phép và fixture đã tính bởi module Người 1-4 tại `tests/fixtures/p019_person5_demo.json`. Fixture là dữ liệu kiểm thử, không phải kết quả một lần gọi LLM thật.

## 2. Hợp đồng đầu vào/đầu ra

`profile`: FinancialProfile **15 khóa** của Người 1. Tiền dạng số VND; tỷ lệ năm dạng thập phân; thiếu dữ liệu là `None`. `notes` không được đưa vào prompt AI như chỉ thị.

`calculation_result`: dictionary của `calculate_financial_metrics` Người 2 bản **FIXED**, gồm `fv_total`, `adjusted_goal_amount`, `goal_gap`, dòng tiền, khoản đóng góp, giả định và cảnh báo. `goal_gap > 0` nghĩa là thiếu; `goal_gap <= 0` nghĩa là đạt/vượt. Người 5 chỉ đối chiếu tính nhất quán, không tính lại FV/PMT.

`scenario_result`: nhận trực tiếp `build_scenarios(...)` (`conservative`, `base`, `optimistic`, `metadata`) hoặc bundle của `render_scenario_page(...)`:

```text
scenarios: ba kịch bản nói trên
what_if: kết quả baseline/modified/comparison hoặc None
stress_test: kết quả baseline/stressed/comparison hoặc None
is_final_plan: false
```

Lịch đóng góp trong stress thay đổi; `stressed.calculation_result.monthly_contribution` và `required_monthly_contribution` là `None`. Dùng `comparison` để diễn giải thời điểm đạt và phục hồi. Người 5 chặn baseline/kịch bản cơ sở không khớp hoặc số giảm stress không khớp.

`validation_result`: dictionary 6 khóa của Người 4. Chỉ `VALID`/`WARNING` và `can_simulate=True` mới được giải thích. Cảnh báo vẫn được giữ trong giao diện/PDF. Những trạng thái khác bị chặn.

`generate_report` nhận `results` theo dạng:

```python
{
    "calculation_result": calculation_result,
    "scenario_result": scenario_result,
    "validation_result": validation_result,
    "profile_confirmed": True,
    "assumptions_confirmed": True,
    "report_confirmed": True,
}
```

Ba cờ xác nhận phải là `True`; báo cáo bị từ chối nếu lời giải thích có số chưa đối chiếu được hoặc kết luận từng kịch bản trái với Python. Hàm trả đường dẫn PDF, không sửa input. Giao diện `render_report_page(profile, calculation_result, scenario_result, validation_result, *, profile_confirmed=False, assumptions_confirmed=False) -> dict | None` tự hỏi xác nhận báo cáo lần cuối và trả bundle gồm bytes PDF chỉ khi người dùng đã tạo báo cáo.

## 3. Chế độ AI và giới hạn kiểm tra

- Nếu có `OPENAI_API_KEY`, dùng cùng `OPENAI_MODEL` và `OPENAI_TIMEOUT_SECONDS` với Người 4. Yêu cầu AI trả hai đoạn **định tính** theo JSON schema; phần số, trạng thái đạt/thiếu và cảnh báo do Python dựng. Mô tả gốc trong `notes` không gửi vào lời gọi này. Không hard-code key hay in raw provider payload.
- Nếu không có key, API lỗi hoặc đầu ra không đạt quy tắc, dùng bản giải thích từ Python và **ghi nhãn ngoại tuyến/dự phòng**. Không tính nó là thành tích LLM.
- Bộ lọc chặn chữ số trong đoạn AI, câu cam kết lợi nhuận, khuyến nghị mua/bán cụ thể và kết luận đạt/thiếu do AI tự viết. Kiểm tra numeric grounding tự động không chứng minh mọi ngữ nghĩa; trước khi trình bày kết quả LLM thực tế, cần đọc kiểm tra các nhận định định tính.
- Cấu hình lợi suất trong `config/scenario_defaults.json` là giới hạn mô phỏng cho bài tập, không phải dữ liệu lãi suất thị trường. `expected_income_growth` trong profile không tự được áp vào engine của MVP.

## 4. Cách chạy module độc lập

Khuyến nghị Python 3.12. Từ thư mục `person5/`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-person5.txt
.venv/bin/python -m pytest -q tests/test_llm_outputs.py
.venv/bin/python -m streamlit run ui/report_page.py
```

Trên Windows thay `.venv/bin/python` bằng `.venv\\Scripts\\python.exe`. Giao diện chạy độc lập dùng fixture P019 được gắn nhãn demo; phải đánh dấu xác nhận hồ sơ và giả định mẫu rồi mới tạo lời giải thích/PDF. Không có API key vẫn xem được báo cáo ngoại tuyến. Khi nhóm ghép, chạy lệnh từ thư mục gốc project để `src`/`ui` import đúng.

## 5. Hướng dẫn ghép, không viết `app.py` trong gói này

1. Lấy `src/schemas.py` và `data/` từ Người 1; `src/calculations.py` bản **FIXED** từ Người 2; đúng sáu file sở hữu Người 3; đúng năm file sở hữu Người 4. **Không chép nguyên thư mục demo** từ ZIP Người 3/4. Không dùng `calculations.py` cũ có trong ZIP Người 1.
2. Chép đúng file Người 5 vào các đường dẫn tương ứng và gộp dependencies, giữ `assets/` cạnh `src/`. Không thay thế module của người khác.
3. Sau xác nhận dữ liệu ở Bước 2, gọi validation/Person 3 với giả định hiện tại. Nếu trang Người 3 đổi lợi suất/lạm phát, validation phải chạy trên **giả định cơ sở cuối cùng**; app tích hợp cập nhật `assumptions_confirmed=True` cho kết quả vừa tính. Giao diện demo độc lập vẫn yêu cầu xác nhận giả định mẫu; caller phải xóa kết quả cũ nếu hàm trả `None`.
4. Có thể dùng `scenario_output["scenarios"]["base"]["calculation_result"]` làm `calculation_result` vì đó là kết quả engine Người 2 của kịch bản cơ sở. Truyền toàn bộ `scenario_output` cho Người 5, không bỏ `what_if`/`stress_test` nếu muốn giải thích hai phần này.
5. Chỉ gọi `render_report_page(...)` khi có bundle xác nhận mới nhất; nếu upstream trả `None` hoặc dữ liệu đổi, không giữ báo cáo PDF cũ. Người 5 tự xóa state có tiền tố `person5_` khi input được truyền vào thay đổi, không xóa state thành viên khác.

Chưa có `app.py` tích hợp năm người trong các gói được cung cấp. Integration test toàn hệ thống và dashboard cuối là công việc **chung của nhóm sau bàn giao**, đúng file kế hoạch.

## 6. Evaluation và failure cases

`evaluation_results.csv` ghi số đã đo và `not_measured` riêng. Trên **20 hồ sơ giả lập**, khi chỉ chấm *trường bắt buộc bị thiếu* (không tính `expected_income_growth` tùy chọn), rule Người 4 có TP=19, FP=0, FN=0: precision/recall/F1 đều 1,000. Đây là kết quả validation bằng Python trên hồ sơ ground truth, **không phải** độ chính xác trích xuất LLM hay phát hiện mọi mâu thuẫn.

Đã kiểm tra bản P019 ngoại tuyến: baseline 130 triệu, stress 118 triệu; chậm 3 tháng so với baseline và muộn 1 tháng so với hạn gốc. Numeric screen trên mẫu ngoại tuyến không phát hiện số/đơn vị ngoài dữ liệu nguồn; đây không phải điểm groundedness của LLM thật. Field accuracy, completeness và baseline form-vs-LLM cần API/user study mới đo được.

Ba ca lỗi có phân tích nguyên nhân, được kiểm thử bằng **injection có chủ đích**, không giả làm lỗi từ API thật:

| Ca | Nguyên nhân | Kết quả kiểm tra/xử lý |
|---|---|---|
| AI thêm `999.999.999 VND` | Số không nằm trong JSON Python | Bỏ bình luận AI hoặc chặn PDF nếu số được đưa từ bên ngoài |
| AI nói “chắc chắn đạt mục tiêu” | Cam kết và tự kết luận thay Python | Bỏ bình luận, hiển thị bản ngoại tuyến được ghi nhãn |
| Kết quả stress/baseline bị đổi sau khi tính | Kết quả cũ hoặc payload ghép nhầm | `stale_result`/`inconsistent_result`, yêu cầu tính lại trước báo cáo |

Các failure cases LLM thật và tỷ lệ lỗi có tần suất phải đo sau khi nhóm cấp API/key và chạy bộ test. Không điền số giả vào bảng.

## 7. Kiểm thử đã thực hiện và giới hạn

- Test Người 5 chạy trên Python 3.12, kiểm tra fixture P019 thực từ API Python Người 1-4, các ca chặn, cấu trúc/bytes/text PDF và Streamlit AppTest.
- PDF mẫu là A4, tiếng Việt Unicode, được render và rà soát hai trang; giấy phép font nằm trong `assets/FONT_LICENSE.txt`.
- API LLM thật chưa chạy vì không có API key được cung cấp. Test AI dùng mock; kết quả mock không chứng minh độ chính xác LLM hay chất lượng ngữ nghĩa trên câu tự do.
- Không tuyên bố đã có ứng dụng web cuối hoặc đã pass integration test năm module; đó là bước tiếp theo của cả nhóm theo kế hoạch.
