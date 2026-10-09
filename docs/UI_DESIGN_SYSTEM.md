# Hệ thống giao diện Project 09

> Bản thiết kế lịch sử. Bản hiện tại dùng Electric Sapphire, xem `ELECTRIC_SAPPHIRE.md`; CSS hoạt động là `assets/base.css` và `assets/sapphire.css`. Không còn dùng serif hay hệ màu cream/gold bên dưới.

- **Màu:** ink `#09131E`, navy `#152234`, cream `#F7F3EC`, gold `#A77719` cho nút và trạng thái được chọn; trắng cho mặt đọc. Gold đậm để chữ trắng có độ tương phản tốt.
- **Chữ:** Avenir Next/Helvetica Neue cho nội dung, menu và các tiêu đề quy trình; Iowan Old Style/Baskerville chỉ dùng có chọn lọc ở hero/KPI trên macOS, với fallback hệ thống. Không tải CDN, logo hay video từ DOBN. Ảnh hero tạo riêng, đóng gói WebP trong `static/` và phục vụ nội bộ.
- **Cấu trúc:** menu ngang trắng điều hướng năm màn hình, tiến độ/reset trong popover; không có sidebar. Hero tối toàn màn hình với ảnh bên phải ở Tổng quan; mỗi trang chức năng có banner tối và tiến trình 4 bước. Form hồ sơ mang cấu trúc tài liệu với header navy, năm phần song ngữ, hai cột trên desktop và xếp dọc trên mobile. Card cho KPI; bảng và diễn giải đặt trong expander; Plotly cho chuỗi và so sánh. Không hiển thị JSON kỹ thuật trong luồng tích hợp.
- **Đơn vị:** hiển thị `100.000.000 ₫`, `8,0%`, `36 tháng`; dữ liệu thiếu hiển thị "Chưa đủ dữ liệu" hoặc "Cần bổ sung". Đầu vào vẫn dùng chữ số thô theo parser hiện có.
- **Biểu đồ:** Plotly dùng navy/teal/gold/taupe, sans-serif, grid nhẹ, hover VND chính xác, panel bo góc và shadow tiết chế. Đường liền là số dư; đường chấm là mục tiêu. Bar chart hiển thị trực tiếp giá trị cuối kỳ.
- **Nguồn tham chiếu:** card riêng ghi ngày truy xuất 24/09/2026, giá trị, tên nguồn và link. Snapshot nằm trong `config/market_reference.json` để app chạy offline và có thể truy nguyên.
- **Trạng thái:** cảnh báo của Streamlit cho thiếu hụt dòng tiền; lỗi validation nằm cùng trang nhập/xác nhận; người dùng phải xác nhận trước khi mô phỏng và trước khi xuất PDF.
- **Chuyển động & accessibility:** nền ảnh/ánh sáng chuyển chậm, menu/card phản hồi hover; ba thẻ quy trình nâng, đổi viền và xoay mũi tên khi tương tác, xuất hiện nhẹ theo cuộn ở trình duyệt hỗ trợ. Chữ và form không mờ trong lúc app chạy lại. Các widget Streamlit giữ label/focus; nội dung responsive; `prefers-reduced-motion` tắt hiệu ứng khi người dùng yêu cầu. CSS không điều khiển validation hoặc dữ liệu.
- **Nguồn tham khảo:** ảnh mẫu thứ hai do người dùng cung cấp và gói DOBN: menu ngang, nền xanh đen, chữ serif vàng, ảnh kiến trúc bên phải. Không sao chép tên, logo, thương hiệu hoặc con số của DOBN.

Tệp triển khai: `.streamlit/config.toml`, `assets/styles.css`, `ui/theme.py`.

Menu và tab: font sans 600 áp dụng trực tiếp cho phần chữ bên trong widget, gạch chân vàng có chuyển động. Motion: ảnh zoom chậm, màu vàng dịch nhẹ, card nâng/viền vàng, CTA ánh sáng khi hover. Không áp dụng hiệu ứng mờ cho controls.
