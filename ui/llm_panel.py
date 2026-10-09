"""User-facing provenance. Fixture output is never labeled as a live LLM run."""
from copy import deepcopy
from html import escape
import streamlit as st
from ui.theme import money


FIELD_NAMES = {
    "monthly_primary_income": "Thu nhập chính", "monthly_other_income": "Thu nhập phụ",
    "monthly_essential_expense": "Chi phí thiết yếu", "monthly_discretionary_expense": "Chi phí linh hoạt",
    "monthly_debt_payment": "Trả nợ", "current_savings": "Tiết kiệm",
    "emergency_fund_reserved": "Quỹ dự phòng", "goal_name": "Mục tiêu",
    "goal_amount": "Giá trị mục tiêu", "goal_horizon_months": "Thời hạn (tháng)",
    "risk_tolerance": "Mức rủi ro", "liquidity_need": "Nhu cầu rút tiền",
    "expected_income_growth": "Tăng thu nhập dự kiến",
}


def remember_origin(mode: str, profile: dict, text: str = "", evidence: dict | None = None) -> None:
    st.session_state["profile_origin"] = {
        "mode": mode, "profile": deepcopy(profile), "text": text,
        "evidence": deepcopy(evidence or {}),
    }


def render_llm_roles() -> None:
    st.markdown(
        '<div class="p09-role-grid">'
        '<div><b>AI sắp xếp & diễn giải</b><span>Đọc mô tả thành hồ sơ có cấu trúc; bổ sung nhận xét định tính khi dùng AI trực tuyến.</span></div>'
        '<div><b>Python tính & kiểm tra</b><span>Tính dòng tiền, tiến độ, ba phương án; kiểm tra dữ liệu thiếu và giới hạn đầu ra AI.</span></div>'
        '<div><b>Bạn quyết định</b><span>Sửa bản nháp, xác nhận giả định và duyệt nội dung trước khi xuất báo cáo.</span></div>'
        '</div>', unsafe_allow_html=True)


def render_origin(current: dict) -> None:
    origin = st.session_state.get("profile_origin")
    if not origin:
        return
    mode = origin["mode"]
    label = {"manual": "Hồ sơ nhập thủ công", "demo": "Hồ sơ mẫu",
             "live_llm": "AI tạo bản nháp · cần kiểm tra lại"}.get(mode, "Hồ sơ nhập")
    st.markdown('<span class="p09-badge ' + ('is-demo' if mode == 'demo' else '') + '">' + label + '</span>', unsafe_allow_html=True)
    if mode == "manual":
        return
    with st.expander("Đối chiếu mô tả và bản nháp", expanded=False):
        if mode == "demo":
            st.info("Bản nháp được chuẩn bị sẵn cho hồ sơ mẫu này. Bạn có thể sửa trước khi lập kế hoạch.")
        st.write(origin["text"])
        def display(field, value):
            if value is None:
                return "Chưa có · cần bổ sung"
            if field in ("goal_horizon_months", "goal_name"):
                return str(value)
            if field in ("risk_tolerance", "liquidity_need"):
                return {"low": "Thấp", "medium": "Trung bình", "high": "Cao"}.get(value, str(value))
            if field == "expected_income_growth":
                return f"{value * 100:g}% (chưa áp dụng)"
            return money(value)
        rows = []
        for field, label in FIELD_NAMES.items():
            before = origin["profile"].get(field)
            row = {"Thông tin": label, "Bản nháp ban đầu": display(field, before),
                   "Hiện tại": display(field, current.get(field)),
                   "Đối chiếu": "Đã chỉnh sửa" if before != current.get(field) else "Chưa sửa"}
            if mode == "live_llm":
                row["Thông tin trong mô tả"] = origin["evidence"].get(field) or "Không có"
            rows.append(row)
        st.dataframe(rows, hide_index=True, width="stretch")


def render_llm_showcase() -> None:
    st.markdown("### LLM hỗ trợ ở đâu?")
    render_llm_roles()
    st.markdown("**Minh họa ngoại tuyến:** chọn một mô tả mẫu ở trang Hồ sơ, xem bản nháp tại Xác nhận, "
                "rồi sửa một số tiền để thấy kế hoạch cập nhật. Các phép tính này chạy thật bằng Python.")
    st.caption("Chưa đo chất lượng LLM trực tuyến khi chưa gọi API. Không dùng kết quả fixture hoặc điểm kiểm thử phần mềm làm điểm LLM.")
