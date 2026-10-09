# Báo cáo kiểm thử cuối · 26/09/2026

> Tài liệu này lưu lịch sử các lần kiểm thử trước Electric Sapphire. Kết quả và giới hạn của bản hiện tại nằm trong `SAPPHIRE_QA.md`. Các ghi chú “tự xác nhận”, “PDF luôn đúng 3 trang”, màu/font cũ bên dưới không còn mô tả bản hiện tại.

## Sửa phân trang PDF, font và trích xuất AI · 26/09/2026

- PDF P001 và P019 đều được tạo lại thành đúng 3 trang A4. Stress test được
  đưa vào đầu trang 3 nên không còn trang gần như trống; generator kiểm tra
  chính xác số trang trước khi bàn giao file.
- `outputs/sample_report.pdf` và toàn bộ PDF/PNG QA được tạo lại bằng generator
  hiện hành. P019 giữ đủ số 130.000.000 VND, 118.000.000 VND và phần vượt dòng
  tiền 95.238 VND/tháng.
- Giao diện bỏ serif trang trí và Google Fonts, chuyển sang sans-serif hệ thống;
  PDF tiếp tục dùng Liberation Sans đóng gói sẵn để hiển thị tiếng Việt ổn định.
- Luồng AI không còn lưu hoặc chuyển bước khi kết quả trích xuất không có trường
  tài chính hữu ích. Khóa Google AI Studio `AIza...` được nhận diện và giải thích
  rõ là không tương thích với endpoint OpenAI.
- Python 3.12.14, Streamlit 1.64.0: 57 dependency tương thích, compileall đạt,
  **459 passed, 0 failed** trong 7,71 giây; HTTP health trả `ok`, trang gốc trả 200.
- CSS có 414 cặp dấu ngoặc cân bằng và không còn tải Google Fonts.

## Nghiệm thu dashboard Report premium · 26/09/2026

- AppTest trực tiếp trên trang Báo cáo xác nhận không có exception, có ba biểu
  đồ Plotly và vùng **Xem phân bổ dòng tiền và giả định của báo cáo**.
- Luồng thao tác đã kiểm tra: **Tạo phần giải thích → Tôi đã đọc và xác nhận nội
  dung → Tạo bản PDF hoàn chỉnh → Tải báo cáo PDF**.
- File tạo ra bắt đầu bằng `%PDF`; điều khiển tải xuống chỉ xuất hiện sau khi
  báo cáo được tạo thành công.
- CSS cân bằng 428 cặp dấu ngoặc; các component hero, KPI, tiến trình và trạng
  thái tải xuống đều tồn tại. HTTP health trả `ok`, trang gốc trả 200.
- Python 3.12.14, Streamlit 1.64.0: **457 passed, 0 failed** trong 8,43 giây.

## Nghiệm thu PDF mới và nội dung hướng người dùng · 26/09/2026

- PDF mẫu P019 được tạo bằng luồng thật, gồm 3 trang A4 và ba biểu đồ vector:
  tiến độ mục tiêu, phân bổ dòng tiền, so sánh ba phương án.
- Đã render toàn bộ trang thành PNG ở 140 DPI để kiểm tra trực quan: không có
  trang trắng, chữ bị cắt, bảng tràn, biểu đồ lệch hoặc ký tự tiếng Việt lỗi.
- Nội dung PDF giữ đủ số kiểm thử P019: cơ sở 130.000.000 VND, sau khi thu nhập
  giảm 118.000.000 VND và phần vượt dòng tiền 95.238 VND/tháng.
- AppTest xác nhận phần giải thích hiển thị không còn ghi chú chế độ xử lý hoặc
  câu “mọi số liệu do Python cung cấp”.
- Python 3.12.14, Streamlit 1.64.0: dependency check và compileall đạt;
  `python -m pytest -q` đạt **457 passed, 0 failed** trong 7,34 giây.

## Nghiệm thu luồng Kế hoạch thu gọn · 26/09/2026

- Luồng hiển thị mới: kết luận → KPI → chọn phương án → biểu đồ phương án →
  tiến độ mục tiêu và phân bổ dòng tiền.
- AppTest xác nhận phương án mặc định là **Cơ sở**, trang chỉ còn hai tab công
  cụ, hai mục **Xem so sánh cả ba phương án** và **Xem bảng số liệu chi tiết**
  đều tồn tại ở trạng thái thu gọn; không có exception.
- Python 3.12.14, Streamlit 1.64.0: compileall và dependency check đạt;
  `python -m pytest -q` đạt **457 passed, 0 failed** trong 11,73 giây.
- Không thay đổi schema, calculation engine, scenario engine hoặc stress test.

## Nghiệm thu bản dashboard và callback Xác nhận · 26/09/2026

- Sửa thao tác nạp tình huống mẫu và trích xuất OpenAI ở trang Xác nhận thành
  callback chạy trước khi Streamlit khởi tạo lại widget; không còn lỗi
  `StreamlitWidgetAlreadyInstantiatedError`.
- Cập nhật test theo giao diện hiện hành: hồ sơ được kiểm tra qua session state
  thay cho JSON kỹ thuật; lời giải thích được kiểm tra từ bundle thay cho
  `st.text`; HTTP 401 được phân loại đúng là `api_auth_failed`.
- Python 3.12.14, Streamlit 1.64.0: `python -m pytest -q` đạt **457 passed,
  0 failed** trong 7,78 giây.
- 57 dependency tương thích; compileall đạt; Streamlit headless trả
  `/_stcore/health = ok`.

## Cập nhật API và đánh giá LLM

- Giao diện Hồ sơ giải thích API theo luồng: người dùng chủ động bấm → OpenAI chuyển mô tả thành JSON → Python validation/tính toán. Trạng thái key được hiển thị nhưng không lộ key.
- Thêm `src/evaluation_runner.py` và `ui/evaluation_panel.py`: baseline form chạy tại máy; live LLM chỉ chạy sau nút xác nhận và khi có key.
- Live runner đo extraction accuracy/completeness, thời gian, acceptance qua guardrails và unsafe-output rate; có failure cases và xuất CSV.
- `outputs/evaluation_results.csv` chỉ giữ các số đã đo. Các dòng live LLM rỗng/`not_measured` đã được bỏ; UI sẽ thêm live metrics vào file tải xuống sau lần chạy API thật.
- Không có key trong môi trường đóng gói nên không tạo số LLM giả. Đây là giới hạn bằng chứng cần được hoàn thành trên máy nhóm trước khi nộp bảng kết quả live.

## Bản dữ liệu tham chiếu và biểu đồ mới nhất

- `python -m compileall -q app.py src ui tests` đạt.
- `load_market_reference()` đọc đúng ngày `2026-09-24`; `reference_assumptions()` trả đúng `annual_return_rate=0.059` và `annual_inflation_rate=0.0489`.
- AST của `app.py`, `src/market_reference.py`, `src/charts.py`, `ui/scenario_page.py`, `ui/review_page.py` hợp lệ; số dấu ngoặc CSS cân bằng.
- Các test giao diện được cập nhật theo luồng một xác nhận ở Kiểm tra và tự cập nhật ở Mô phỏng.
- Bộ test và AppTest đã được chạy lại trong môi trường Python 3.12.14; kết quả
  mới nhất là 457 passed.

## Bản form hồ sơ và luồng chuyển bước mới nhất

- `python -m compileall -q app.py src ui` đạt.
- Kiểm tra độc lập `build_manual_profile` với đủ 15 trường đạt; thời hạn giữ kiểu số nguyên và dữ liệu mục tiêu giữ đúng.
- Kiểm tra AST cho năm file UI/app đã sửa đạt; dấu ngoặc CSS cân bằng; không còn khối **Dữ liệu kỹ thuật đã xác nhận** trên trang Kiểm tra.
- Đã nối trạng thái `profile_just_saved` với `st.rerun()` để chuyển tự động Hồ sơ → Kiểm tra; các bước tiếp theo có nút điều hướng rõ ràng.
- Thay đổi trình bày và luồng chuyển bước hiện đã nằm trong bộ 457 test đạt.

## Sửa Hồ sơ và lời giải thích mới nhất

Compileall đạt. Hàm tóm tắt được kiểm tra với tiền, số 0, trường thiếu và HTML
đặc biệt. AppTest và pytest đã được chạy lại trong lần nghiệm thu 26/09/2026.

## Lần chỉnh tab và chuyển động

Các thay đổi CSS và UI nằm trong bản đã đạt 457 test; chuyển động và responsive
vẫn cần một lượt kiểm tra trực quan trên Safari/Chrome.

## Đã chạy thực tế

| Gate | Kết quả |
|---|---|
| Bản dashboard + callback Xác nhận | Python 3.12.14, Streamlit 1.64.0: compileall đạt, 57 dependency tương thích, **457 passed**, 0 failed (7,78 s); HTTP health → `ok` |
| Baseline bản ZIP gốc | `python3 -m pytest -q` → **443 passed**, 0 failed, 0 skipped (16,28 s) |
| Baseline headless | Streamlit bản gốc khởi động, `GET /_stcore/health` → `200 ok` |
| Bản giao diện sửa lần 2 | `bash scripts/verify_project.sh` → compileall đạt, `pip check` không có xung đột, **447 passed**, 0 failed, 0 skipped (10,71 s); log `docs/FINAL_TEST_RUN.log` |
| Bản giao diện theo ảnh mẫu thứ hai | `python -m pytest -q` → **447 passed**, 0 failed, 0 skipped (10,65 s). AppTest bấm nút hero sang Hồ sơ rồi bấm menu về Tổng quan, không có exception. |
| Bản menu ngang và chuyển động | `python -m pytest -q` → **447 passed**, 0 failed, 0 skipped (10,96 s). AppTest đi qua menu Hồ sơ/Xác nhận/Mô phỏng/Báo cáo, reset và P001 tới PDF. HTTP smoke: `/_stcore/health` → 200; `/app/static/hero_office.webp` → 200 `image/webp` (182.450 bytes). |
| Bản chỉnh font và độ rõ | `python -m pytest -q` → **447 passed**, 0 failed, 0 skipped (10,38 s); điều hướng và PDF vẫn đi qua AppTest. Đã bỏ opacity/transform animation trên nội dung tương tác và giảm khoảng trống Hồ sơ. |
| UI integration | Test mới đưa P001 qua review, assumptions, mô phỏng, giải thích và tạo bytes PDF từ app Streamlit AppTest; test reset có xác nhận và invalidation; không có exception |
| HTTP smoke | Streamlit headless khởi động; `GET /_stcore/health` → `200 ok`; `GET /` → `200` (7260 bytes) |
| PDF QA | Báo cáo P001 và P019 sinh bằng code hiện hành: mỗi file đúng 3 trang A4; render toàn bộ trang bằng Poppler, không có trang trắng, chữ cắt hoặc bảng tràn. File bằng chứng nằm tại `docs/QA_P001_report.pdf`, `docs/QA_P019_report.pdf` và `docs/QA_P001_pdf_page_*.png`. |

## Case nghiệp vụ đối chiếu với engine

| Case | Kết quả chạy thật |
|---|---|
| P001 | VALID, thu 10.000.000, chi 7.000.000, cuối kỳ 118.000.000 VND, đạt tháng 30, đóng góp cần thiết 2.500.000 VND/tháng. |
| P009 | NEEDS_CLARIFICATION, `can_simulate=False`, `missing_fields=['goal_horizon_months']`; không gọi engine/report cho profile thiếu thời hạn. |
| P019 | VALID, baseline 130.000.000 VND, stress 118.000.000 VND, chậm 3 tháng so với baseline, trễ 1 tháng so với hạn gốc. |

Kết quả phụ thuộc dữ liệu mẫu cố định trong `data/test_cases.json`. Lời giải thích offline được kiểm tra số trước khi tạo PDF. Không có live OpenAI API call.

## Pending local verification

- Chưa có **ảnh chụp trực tiếp của bản giao diện menu ngang mới** trên trình duyệt. Trình duyệt tự động bị chặn khi mở localhost trong môi trường này; ảnh PDF QA ở trên không được coi là ảnh giao diện. Bố cục và chuyển động cần được nhìn trên máy người dùng để chốt tỷ lệ/độ tương phản.
- Chưa kiểm tra trực quan viewport desktop 1440 px, laptop 1024–1280 px, mobile 375–430 px; cần mở app trên trình duyệt và đối chiếu các màn hình, đặc biệt bảng rộng và biểu đồ.
- Chưa chạy một lượt bấm tay trong trình duyệt. Test Streamlit AppTest đã chạy luồng offline P001 tới PDF nhưng không thay thế kiểm tra thao tác trực quan.
- Live AI, timeout/credential ngoài môi trường mock chưa chạy vì không có key; không bắt buộc cho chế độ nhập thủ công.

Trên macOS có mạng và trình duyệt, chạy:

```bash
cd Project_09_Simple_Professional
bash scripts/verify_project.sh
python -m streamlit run app.py
```

Mở URL Streamlit, thử lần lượt P001, P009, P019 ở chế độ mẫu; chụp năm khu vực ở 1440 px và 390 px. PDF thật tải từ nút Báo cáo; mở bằng Preview và kiểm tra đủ trang, font tiếng Việt, bảng và các con số. Nếu chưa có môi trường Python, chạy `bash scripts/setup_and_run.sh` trước.

**Nghiệm thu runtime:** backend/UI test và HTTP smoke đạt; nghiệm thu hình ảnh responsive và thao tác browser **Pending local verification**.
