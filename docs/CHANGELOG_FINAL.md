# Thay đổi bản giao diện cuối

## PDF ba trang, font sans-serif và chặn hồ sơ AI rỗng · 26/09/2026

- Cố định bố cục PDF thành đúng ba trang cho cả P001 và P019; chuyển stress test
  sang trang 3 và bỏ nội dung lặp để không còn trang gần như trống.
- Generator tự kiểm tra số trang trước khi xuất file; test PDF yêu cầu chính xác
  ba trang thay cho điều kiện cũ chỉ cần ít nhất một trang.
- Thống nhất web về sans-serif hệ thống, bỏ phụ thuộc Google Fonts và serif trang
  trí; PDF giữ Liberation Sans để hiển thị dấu tiếng Việt ổn định.
- Không lưu hồ sơ hoặc chuyển bước nếu AI trả kết quả không có dữ liệu tài chính
  hữu ích; nhận diện khóa Google AI Studio đặt nhầm vào cấu hình OpenAI.
- Khi hồ sơ thiếu quá nhiều trường, trang Xác nhận hiển thị một hướng dẫn gọn và
  thu danh sách chi tiết vào vùng mở rộng thay vì phủ kín màn hình.
- Nghiệm thu cuối: 57 dependency tương thích, compileall đạt, **459 test pass**,
  HTTP health `ok`; P001 và P019 đều xuất đúng ba trang.

## Dashboard Report premium trên web · 26/09/2026

- Thiết kế lại toàn bộ màn Báo cáo theo phong cách dashboard tài chính cao cấp,
  đồng bộ navy/teal/gold với PDF mới.
- Thêm hero kết luận, trạng thái đạt mục tiêu, bốn KPI và khối lưu ý gọn.
- Mặc định hiển thị biểu đồ tiến độ mục tiêu và so sánh ba phương án; biểu đồ
  phân bổ dòng tiền, bảng chỉ số và giả định được thu vào một vùng mở rộng.
- Thay luồng nút rời rạc bằng tiến trình ba bước: tạo giải thích, xác nhận nội
  dung và tải báo cáo PDF.
- AppTest xác nhận 3 biểu đồ, trạng thái điều khiển và PDF tải xuống hoạt động;
  toàn bộ **457 test** đạt, HTTP health trả `ok`.

## Báo cáo PDF hiện đại và làm sạch nội dung web · 26/09/2026

- Thiết kế lại PDF thành báo cáo ba trang theo phong cách tài chính hiện đại,
  sử dụng hệ màu navy/teal/gold, phân cấp rõ và khoảng trắng cân đối.
- Bổ sung ba biểu đồ vector sắc nét: tiến độ mục tiêu, phân bổ dòng tiền hằng
  tháng và so sánh giá trị cuối kỳ của ba phương án.
- Thêm kết luận chính, bốn KPI, bảng so sánh, kết quả khi điều chỉnh kế hoạch,
  kiểm tra khi thu nhập giảm và lưu ý sử dụng.
- Thay các câu hướng tới lập trình viên trên giao diện bằng ngôn ngữ người dùng;
  ẩn mã lỗi, tên module, engine, schema, fixture và ghi chú chế độ xử lý.
- Render trực quan mẫu P019: 3 trang A4, không trang trắng, không tràn chữ hoặc
  chồng lấn. Toàn bộ **457 test** đạt.

## Thu gọn dashboard Kế hoạch · 26/09/2026

- Sắp xếp lại luồng Kế hoạch theo thứ tự: kết luận, KPI, phương án đang chọn,
  dashboard tổng quan, rồi mới đến các công cụ thử thay đổi và stress test.
- Mặc định chỉ hiển thị biểu đồ của phương án đang chọn, tiến độ mục tiêu và
  phân bổ dòng tiền.
- Thu hai biểu đồ đối chiếu vào **Xem so sánh cả ba phương án** và bảng kỹ
  thuật vào **Xem bảng số liệu chi tiết**; bỏ tab Ba phương án bị trùng nội dung.
- Không thay đổi schema, phép tính, scenario engine hoặc stress-test engine.

## Sửa callback và nghiệm thu dashboard · 26/09/2026

- Chuyển nạp tình huống mẫu và trích xuất OpenAI ở trang Xác nhận sang callback,
  tránh ghi vào session state sau khi widget đã được khởi tạo.
- Cập nhật test theo giao diện tóm tắt mới và mã lỗi xác thực API 401.
- Python 3.12.14, Streamlit 1.64.0: **457 passed, 0 failed**; compileall,
  dependency check và HTTP health đều đạt.

## Typography, dữ liệu tham chiếu và biểu đồ · 24/09/2026

- Đổi tiêu đề phần quy trình sang sans-serif hiện đại; thay ba ô biểu tượng xanh bằng icon SVG nét mảnh trên nền vàng nhạt, không dùng ảnh/CDN.
- Rút hai xác nhận ở màn Kiểm tra thành một xác nhận dữ liệu; bỏ xác nhận lặp ở màn Mô phỏng. Mô phỏng tự tính lại khi lợi suất hoặc lạm phát thay đổi; vẫn giữ xác nhận cuối trước khi tạo PDF.
- Bổ sung snapshot `config/market_reference.json`, ngày truy xuất 24/09/2026: lợi suất tiền gửi VND 12 tháng Vietcombank 5,90%/năm; CPI tháng 8/2026 tăng 4,89% YoY qua Vnstock Macro, đối chiếu Cục Thống kê.
- Hiển thị ngày, giá trị, nguồn và liên kết kiểm chứng trong card tham chiếu trên màn Mô phỏng. Không gọi mạng khi app chạy.
- Thiết kế lại biểu đồ Plotly: palette navy/teal/gold/taupe, font sans, grid nhẹ, line spline, hover chính xác VND, panel bo góc, thanh so sánh có nhãn và bo góc.
- Compileall, AST, parser snapshot và cân bằng CSS đạt; môi trường hiện tại không có Streamlit/Plotly/pytest để chạy lại browser/AppTest.

## Form hồ sơ, thẻ quy trình và luồng chuyển bước

- Thiết kế lại ba thẻ **Hiểu dòng tiền / Thử điều kiện khác / Đọc báo cáo** thành khối quy trình editorial có biểu tượng, phân cấp thông tin, nhãn chức năng và chuyển động hover/scroll.
- Thiết kế lại form nhập thành hồ sơ tài chính có header navy, tiêu đề song ngữ, năm khu vực rõ ràng, ô nhập nền ivory, placeholder và trạng thái focus màu vàng.
- Nút **Lưu hồ sơ và tiếp tục** tự chuyển sang tab **Kiểm tra** sau khi lưu thành công. Bổ sung nút đi tiếp từ Kiểm tra sang Mô phỏng và từ Mô phỏng sang Báo cáo.
- Loại khối JSON kỹ thuật khỏi màn Kiểm tra, Mô phỏng và chi tiết dòng tiền; thay bằng bảng hoặc diễn giải dễ đọc.
- Compileall, parser hồ sơ 15 trường, cân bằng dấu ngoặc CSS và kiểm tra tĩnh raw-output đạt. Môi trường hiện tại không có Streamlit/pytest nên chưa chạy lại runtime; kết quả 447 test là của bản trước.

## Hồ sơ dễ đọc và giải thích không hiển thị code

- Thay JSON nháp bằng bản tóm tắt đủ 15 trường với nhãn tiếng Việt, định dạng tiền, tỷ lệ và mức rủi ro. Nội dung được escape HTML.
- Bổ sung nút đi tiếp tới Xác nhận; đổi nhãn mẫu và thông báo kỹ thuật thành câu dễ hiểu.
- Mở rộng vùng nhập, làm rõ viền và nền ô nhập, nhóm lựa chọn cách nhập.
- Lời giải thích báo cáo dùng font nội dung thông thường; loại JSON giả định/metadata khỏi trang Báo cáo.
- Compileall đạt; kiểm tra độc lập định dạng, số 0, thiếu dữ liệu và escape HTML đạt. Chưa chạy lại Streamlit/pytest do môi trường hiện tại thiếu dependencies.

## Tinh chỉnh tab và chuyển động

- Đặt font trực tiếp trên đoạn chữ trong nút Streamlit, giảm độ đậm còn 600 và đồng bộ các tab mô phỏng.
- Gạch chân vàng chuyển động và nền chọn nhẹ; ảnh hero zoom chậm; tiêu đề ánh vàng chuyển nhẹ; nút có vệt sáng khi hover; thẻ và KPI nâng nhẹ.
- Thẻ xuất hiện theo cuộn ở trình duyệt hỗ trợ animation-timeline; không giảm opacity của chữ. Reduce Motion tắt toàn bộ hiệu ứng.
- Chỉ sửa CSS. Môi trường hiện tại không có pytest/Streamlit để chạy lại kiểm tra runtime; kết quả 447 test bên dưới thuộc bản trước.

## Chỉnh kiểu chữ và khả năng đọc · 24/09/2026

- Dùng Avenir Next/Helvetica Neue cho nội dung và Iowan Old Style/Baskerville cho tiêu đề trên macOS, có font dự phòng; tăng độ tương phản và cỡ chữ menu.
- Viết lại CSS thành một hệ quy tắc thống nhất, bỏ các lớp ghi đè cũ gây kết quả khó đoán.
- Bỏ hiệu ứng mờ/dịch chuyển trên điều khiển và form mỗi lần app chạy lại; giữ chuyển động nền chậm và phản hồi hover.
- Đưa lựa chọn nguồn trích xuất AI vào mục mở rộng, để màn Hồ sơ bắt đầu bằng lựa chọn cách nhập và form. Căn giữa banner, giảm khoảng trống dọc.
- Kiểm tra sau sửa: **447 passed**; chưa có ảnh chụp trực tiếp phiên Safari đã tải xong.

## Sửa theo ảnh chụp màn hình mới · 24/09/2026

- Loại bỏ sidebar điều hướng khỏi màn hình; năm nút trang chủ, hồ sơ, kiểm tra, mô phỏng và báo cáo được hiển thị trực tiếp trên menu trắng có biểu tượng và gạch chân trạng thái.
- Đưa tiến độ phiên và nút reset có xác nhận vào menu **Tiến độ**.
- Mỗi bước có banner xanh đậm, tiêu đề serif và thanh tiến độ bốn bước phía trên form/kết quả, lấy nhịp bố cục từ màn hình dịch vụ của trang tham khảo.
- Thêm chuyển động mở trang, ảnh nền di chuyển nhẹ, ánh sáng nền, hover menu và card; tôn trọng Reduce Motion.
- Ảnh WebP được phục vụ như file tĩnh để tránh gửi ảnh dạng base64 trong mỗi lần app chạy lại. HTTP smoke kiểm tra ảnh trả `200 image/webp`.
- Điều chỉnh kiểm tra UI theo menu mới; **447 passed**, không có exception trong luồng P001 tới PDF.

## Sửa giao diện theo ảnh mẫu thứ hai · 24/09/2026

- Thay trang chủ kiểu card sáng bằng hero tối toàn màn hình, nội dung trái và ảnh văn phòng bên phải; chữ serif trắng/vàng và bảng thống kê quy trình.
- Thêm menu ngang trắng với năm nút chuyển trang thật; sidebar tiến độ vẫn có thể mở khi cần.
- Ảnh nền mới được tạo riêng, lưu offline trong `assets/hero_office.webp`; không dùng logo, video hay con số doanh nghiệp trong ảnh DOBN.
- Form và kết quả được đặt trong vùng đọc riêng; giữ nguyên luồng, engine và API. `447 passed`; AppTest bấm CTA và menu qua lại không có exception.
- Chưa có ảnh chụp trực tiếp giao diện Streamlit trên trình duyệt ở môi trường hiện tại; cần đối chiếu trực quan trên máy người dùng.

## Sửa giao diện lần 2

- Bỏ các tiêu đề trùng nhau giữa lớp điều phối và từng trang; thay bằng nhãn bước nhỏ.
- Thiết kế lại màn hình tổng quan, sidebar tiến độ, hệ thống màu/chữ, trạng thái điều hướng và bề mặt form.
- Chia form nhập và form duyệt thành hai cột ở màn hình rộng; thu gọn dữ liệu JSON, bảng kỹ thuật, đồ thị phụ và bản dự phóng theo tháng vào mục xem chi tiết.
- Đưa ba KPI cơ sở lên trước các tab kịch bản; phần dòng tiền chi tiết vẫn lấy từ engine và mở được theo nhu cầu.
- Không đổi schema, phép tính, API công khai hoặc giới hạn validation. Toàn bộ 447 test đạt sau sửa.

## Bản tích hợp trước đó

- Giữ nguyên `src/schemas.py`, `src/validation.py`, `src/calculations.py`, `src/scenarios.py`, `src/stress_test.py`, `src/llm_extraction.py`, `src/llm_explanation.py`, `src/evaluation.py` và bảy API công khai.
- Thêm theme offline, CSS, sidebar tiến độ và xác nhận reset; overview có CTA và mô tả rõ mục đích giáo dục.
- Nhóm form theo thu nhập, chi tiêu, tiết kiệm, mục tiêu; trang review có bảng đối chiếu từng trường, trạng thái và nguồn.
- Dashboard hiển thị KPI, mục tiêu và thiếu hụt khả năng chi trả từ engine; biểu đồ có theme thống nhất; các tab mô phỏng dùng nhãn tiếng Việt.
- Trang báo cáo xem trước KPI và phân biệt nội dung giải thích; PDF bổ sung thời điểm tạo UTC.
- Thêm script setup/verify, tài liệu luồng state, thiết kế và báo cáo nghiệm thu.
- Không thay đổi phép tính, schema 15 trường, validation status hoặc JSON keys của assumptions.
# 25/09/2026 - API clarity and measured evaluation

- Replaced the technical API selector copy with a plain-language three-step explanation, explicit privacy/cost boundary and secret-free connection status.
- Added measured structured-form baseline on 20 synthetic profiles.
- Added opt-in live OpenAI evaluation for extraction accuracy, completeness, guardrail groundedness proxy, hallucination/unsafe-output rate, latency and failure cases.
- Added form-versus-LLM comparison and downloadable measured-only CSV.
- Removed blank `not_measured` live rows from the packaged evaluation CSV; the app never fabricates a live score when no API call has run.
- Added `docs/API_AND_EVALUATION_GUIDE.md` for presentation and handoff.
- Cleaned the deliverable packaging so `.venv`, Python caches and macOS metadata are not included.
