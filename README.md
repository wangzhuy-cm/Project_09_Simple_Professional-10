# Project 09 · Electric Sapphire

Web lập kế hoạch tài chính theo mục tiêu, phát triển trên nền Streamlit/Python của dự án gốc. Bản này giữ công thức và hợp đồng 15 trường, làm lại giao diện, luồng xác nhận và PDF.

## Chạy web

Giải nén, mở thư mục `Project_09_Simple_Professional` trong VS Code. Với macOS/Linux:

```bash
bash scripts/setup_and_run.sh
```

Lần đầu cần mạng để cài thư viện. Mở `http://localhost:8501` nếu trình duyệt không tự mở. Khuyến nghị Python 3.12. Không cần API cho nhập tay, mẫu ngoại tuyến, mô phỏng, diễn giải Python và PDF.

Cài thủ công:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Trên Windows: dùng `py -m venv .venv`, sau đó `.venv\Scripts\activate` và hai lệnh `python` cuối. Khi cập nhật từ bản cũ, cài lại `requirements.txt` để có thư viện xem trước PDF. Không chép đè thư mục `.venv` của bản cũ vào gói này.

## Trải nghiệm mới

1. **Hồ sơ:** mục tiêu → thu/chi → tiết kiệm → ưu tiên. Nhập 0 nếu không có khoản thu/chi, để trống nếu chưa biết. Có hướng dẫn bên cạnh và dữ liệu được điền lại khi quay về.
2. **Xác nhận:** đọc sáu chỉ số chính, mở phần sửa khi cần. Mẫu/AI có nhãn nguồn và bảng đối chiếu bản nháp với giá trị đã sửa. Chỉ hồ sơ hợp lệ và được xác nhận mới đi tiếp.
3. **Kế hoạch:** kết luận và ba biểu đồ mặc định: tiến độ mục tiêu, phân bổ dòng tiền, đường số dư của phương án đang chọn. Chọn **Thận trọng / Cơ sở / Tích cực** để đổi cả ba biểu đồ. So sánh toàn bộ, bảng chi tiết, what-if và giảm thu nhập đều thu gọn.
4. **Báo cáo:** diễn giải → duyệt nội dung → tạo, xem trước và tải PDF thật. Có nút quay về Kế hoạch và quay thẳng về Xác nhận.

Trang chủ giữ bố cục gốc, đổi sang sapphire/cyan/violet. Web và PDF đều có bộ chữ Liberation Sans tiếng Việt đóng gói sẵn, không tải Google Fonts. CSS đang dùng: `assets/base.css` + `assets/sapphire.css`; `assets/styles.css` là bản lịch sử, không còn nạp.

## Xác nhận và dữ liệu phiên

Giao diện mặc định tập trung vào lập kế hoạch; ghi chú triển khai nằm trong `docs/NOTES_FOR_PRESENTATION.md`. Bảng đánh giá kỹ thuật chỉ hiện khi đặt `PROJECT09_SHOW_TECHNICAL=1` trước khi chạy. Nhãn nguồn dữ liệu, giả định, cảnh báo và xác nhận vẫn hiển thị cho người dùng.

- Bước Xác nhận có bảng **Mục tiêu, nguồn lực và ràng buộc**: mục tiêu chính, thời hạn, tiết kiệm sau khi giữ quỹ dự phòng, dòng tiền, mức rủi ro/thanh khoản, lỗi/cảnh báo và câu hỏi bổ sung. Bảng cập nhật khi sửa hồ sơ, không tự điền số 0 cho dữ liệu thiếu.
- Bảng này được Python tổng hợp, không gọi API kể cả khi đã cấu hình khóa. Đây là phần hỗ trợ kiểm tra hồ sơ, **không phải kết quả LLM phân rã mục tiêu**. Tích hợp trích xuất và bình luận LLM vẫn cần chạy trực tuyến riêng để nghiệm thu yêu cầu của đề.

- Có thể xem trước kết quả ngay khi thay giả định. Muốn xuất báo cáo phải tích **Tôi đã xem và xác nhận các giả định, phép thử của báo cáo**.
- Thay lợi suất, lạm phát hoặc thông số what-if/stress sẽ bỏ xác nhận đó và vô hiệu hóa báo cáo cũ. Chỉ đổi phương án đang xem không làm mất xác nhận.
- Sửa hồ sơ tại Xác nhận sẽ hủy xác nhận hồ sơ và kết quả phụ thuộc. Nút quay lại không xóa dữ liệu đã lưu trong phiên.
- Dữ liệu chỉ ở phiên Streamlit; tải lại trang, ngắt kết nối hoặc tạo phiên mới có thể mất dữ liệu. Đây chưa phải sản phẩm có tài khoản và cơ sở dữ liệu.
- **Tiến độ → xác nhận bắt đầu phiên mới → Xóa dữ liệu phiên này** là thao tác reset chủ động.

## LLM hỗ trợ như thế nào?

| Phần việc | Ai làm? | Minh chứng trong web |
|---|---|---|
| Đọc mô tả thành hồ sơ | LLM khi chọn AI trực tuyến | Bản nháp, trích dẫn gốc và bảng đối chiếu ở Xác nhận |
| Kiểm tra thiếu/sai và phạm vi | Python | Câu hỏi bổ sung, lỗi và khóa bước tiếp theo |
| Tính dòng tiền, FV, khoản góp, ba phương án | Python | Biểu đồ và bảng chi tiết lấy từ engine |
| Diễn giải số liệu | Mẫu câu Python; LLM có thể thêm nhận xét định tính | Nhãn nguồn ngay trên phần giải thích và trong PDF |
| Duyệt dữ liệu và giả định | Người dùng | Các ô xác nhận tách biệt |

**Mẫu ngoại tuyến là kết quả soạn sẵn trên fixture, không phải phản hồi đã ghi lại của LLM và không phải điểm chất lượng LLM.** Không dùng từ “AI đã xử lý” cho bản mẫu. Đổi nội dung mẫu sẽ không được tự phân tích ngoại tuyến; hãy nhập tay hoặc dùng AI trực tuyến.

Chế độ báo cáo mặc định `use_llm=False`: không gọi API kể cả khi có sẵn khóa. Để gọi thật, người dùng phải bật **Bổ sung nhận xét AI trực tuyến**, đọc thông tin gửi đi rồi bấm tạo. LLM không được tính lại số liệu hoặc đưa kết luận định lượng thay Python. Guardrail chỉ là sàng lọc tự động, không bảo đảm hiểu đúng mọi ngữ nghĩa.

Hết API vẫn có thể trình bày luồng với P001 (đủ thông tin), P009 (thiếu thời hạn), P019 (minh họa cú sốc thu nhập). Xem lời thoại trong `docs/ELECTRIC_SAPPHIRE.md`.

## API tùy chọn

Sao chép `.env.example` thành `.env`, đặt khóa OpenAI của bạn trên máy, không đưa `.env` vào Git/ZIP. Trích xuất trực tuyến chỉ gửi phần mô tả sau khi bạn đồng ý. Nhận xét báo cáo gửi mục tiêu và kết quả tính toán, không gửi ghi chú gốc. Khóa có cấu hình không đồng nghĩa còn hạn mức hoặc có quyền truy cập mô hình. Mất kết nối/hết hạn mức: ứng dụng báo lỗi an toàn; nhập tay và diễn giải Python vẫn hoạt động.

`extract_profile(text) -> dict` giữ đúng 15 trường. `extract_profile_with_evidence(text)` là API bổ sung, tách bằng chứng ra ngoài profile. Các hàm công khai cũ vẫn được giữ.

## Phạm vi và giả định cần nói rõ

- Mục tiêu nhập là giá trị theo giá hôm nay, sau đó điều chỉnh lạm phát. Nếu đó là khoản tiền cố định ở hạn tương lai, đặt lạm phát bằng 0.
- Lợi suất/lạm phát mặc định `5,90%` / `4,89%` là giá trị giữ từ gói gốc. Bản này **chưa xác minh lại** các giá trị đó với nguồn. Ngày, giá trị và liên kết chỉ để truy nguyên/tham khảo; không gọi là dữ liệu thị trường hiện hành.
- Nhập nhu cầu rút tiền và tăng thu nhập chỉ để ghi nhận bối cảnh; chưa tác động công thức.
- Stress tính giảm thu nhập tạm thời. Thiếu hụt sinh hoạt được hiển thị riêng, chưa khấu trừ vào quỹ dự phòng hoặc tiền mục tiêu: kết quả có điều kiện nếu cần nguồn bù.
- Không tính thuế, phí, biến động lợi suất, xác suất thành công hoặc phân bổ sản phẩm đầu tư. Báo cáo lấy phương án cơ sở làm kế hoạch chính; hai phương án còn lại để so sánh.
- Không phải tư vấn đầu tư, không cam kết lợi nhuận hoặc đạt mục tiêu.

## Kiểm thử và PDF mẫu

```bash
python -m pytest -q
python scripts/build_sample_reports.py
```

`outputs/sample_report.pdf` là báo cáo mẫu hiện tại. Mẫu chuẩn có 3 trang A4, năm biểu đồ vector nếu có stress, phông tiếng Việt nhúng. Nội dung dài được phép chuyển thêm trang thay vì báo lỗi hoặc cắt mất nội dung.

`docs/SAPPHIRE_QA.md` ghi kết quả kiểm thử mới và giới hạn kiểm tra trực quan. Các tài liệu handoff, log và ghi chú phiên bản cũ trong `docs/` giữ lại để truy nguyên; khi khác nhau, dùng README này và tài liệu Electric Sapphire.
