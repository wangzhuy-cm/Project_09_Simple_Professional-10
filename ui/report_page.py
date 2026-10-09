"""Person 5: minimal Streamlit review, explanation and PDF download page.

The final app must pass fresh, confirmed upstream data. This page never edits
Person 1-4 state and invalidates its own output when inputs change.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
import json
from pathlib import Path
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

from src.charts import (create_cashflow_chart, create_final_value_chart,
                        create_goal_progress_chart)
from src.llm_explanation import ExplanationError, generate_explanation_result
from src.report_generator import ReportError, generate_report
from src.report_preview import render_pdf_page
from pypdf import PdfReader
from io import BytesIO
from ui.theme import money, percent


PREFIX = "person5_"


def _fingerprint(*values) -> str:
    return sha256(json.dumps(values, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, default=str).encode("utf-8")).hexdigest()


def _invalidate() -> None:
    import streamlit as st
    for name in ("explanation", "explanation_meta", "report_bytes", "report_confirmed", "generated_at"):
        st.session_state.pop(PREFIX + name, None)


def _format_explanation_for_display(value: str) -> str:
    """Present the useful explanation without internal processing notes."""
    headings = {
        "TÓM TẮT HỒ SƠ VÀ DÒNG TIỀN": "Tóm tắt hồ sơ và dòng tiền",
        "BA KỊCH BẢN (THEO GIẢ ĐỊNH)": "Diễn giải ba phương án",
        "WHAT-IF": "Khi điều chỉnh kế hoạch",
        "STRESS TEST": "Khi thu nhập giảm",
        "GIẢ ĐỊNH VÀ CẢNH BÁO": "Giả định và lưu ý",
        "BÌNH LUẬN AI (ĐỊNH TÍNH)": "Nhận xét bổ sung từ AI",
    }
    blocks = []
    for raw_line in str(value).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("Chế độ:"):
            continue
        if line in headings:
            blocks.append("<h4>" + escape(headings[line]) + "</h4>")
        else:
            blocks.append("<p>" + escape(line) + "</p>")
    return "".join(blocks)


def _scenario_map(value: dict) -> dict:
    scenarios = value.get("scenarios", value) if isinstance(value, dict) else {}
    return scenarios if isinstance(scenarios, dict) else {}


def _report_warning_messages(calculation_result: dict, validation_result: dict) -> list[str]:
    messages = []
    gap = calculation_result.get("required_contribution_gap", 0)
    if isinstance(gap, (int, float)) and gap > 0:
        messages.append(
            "Khoản cần dành mỗi tháng đang cao hơn dòng tiền còn lại " + money(gap) +
            ". Hãy cân nhắc điều chỉnh mục tiêu, thời hạn hoặc chi tiêu."
        )
    for warning in validation_result.get("warnings", []):
        message = (warning.get("message", warning.get("code", ""))
                   if isinstance(warning, dict) else str(warning))
        if message and message not in messages:
            messages.append(message)
    return messages


def render_report_page(profile: dict, calculation_result: dict, scenario_result: dict,
                       validation_result: dict, *, profile_confirmed: bool = False,
                       assumptions_confirmed: bool = False) -> dict | None:
    """Display Person 5 outputs and return a confirmed report bundle or None.

    The caller must pass the current outputs of People 1-4 and true human
    confirmation flags. VALID/WARNING and can_simulate are necessary but do not
    replace confirmation. The page asks for a final report confirmation. It
    returns None until a downloadable PDF exists; no other module state is
    mutated. Catches controlled explanation/report errors in the UI.
    """
    import streamlit as st

    with st.container(key="p09_accessible_report_title"):
        st.header("Báo cáo kế hoạch")
    ready = (isinstance(validation_result, dict)
             and validation_result.get("status") in {"VALID", "WARNING"}
             and validation_result.get("can_simulate") is True
             and profile_confirmed is True and assumptions_confirmed is True)
    if not ready:
        _invalidate()
        st.info("Hãy hoàn thành bước Kiểm tra và Kế hoạch trước khi tạo báo cáo.")
        return None
    if not all(isinstance(value, dict) for value in (profile, calculation_result, scenario_result)):
        _invalidate()
        st.error("Thiếu dữ liệu tính toán hoặc kịch bản hiện tại.")
        return None
    try:
        signature = _fingerprint(profile, calculation_result, scenario_result, validation_result)
    except (TypeError, ValueError):
        _invalidate()
        st.error("Dữ liệu kết quả không thể kiểm tra; cần chạy lại mô phỏng.")
        return None
    if st.session_state.get(PREFIX + "signature") != signature:
        _invalidate()
        st.session_state[PREFIX + "signature"] = signature

    scenarios = _scenario_map(scenario_result)
    base_scenario = scenarios.get("base")
    if not isinstance(base_scenario, dict):
        _invalidate()
        st.error("Chưa tìm thấy phương án cơ sở để tạo báo cáo.")
        return None
    goal = float(calculation_result["adjusted_goal_amount"])
    projected = float(calculation_result["fv_total"])
    progress = projected / goal * 100 if goal > 0 else 0
    reached = bool(calculation_result["goal_reached_by_horizon"])
    goal_gap = float(calculation_result["goal_gap"])
    if reached and abs(goal_gap) < .5:
        result_label = "Đạt đúng mục tiêu"
    elif reached:
        result_label = "Vượt mục tiêu " + money(abs(goal_gap))
    else:
        result_label = "Còn thiếu " + money(max(goal_gap, 0))
    month = calculation_result.get("estimated_month_to_goal")
    timing = (f"Dự kiến đạt vào tháng {int(month)}" if month is not None
              else "Chưa xác định thời điểm đạt mục tiêu")
    status_label = "ĐẠT MỤC TIÊU" if reached else "CẦN ĐIỀU CHỈNH"
    status_class = "is-positive" if reached else "is-warning"
    goal_name = escape(str(profile.get("goal_name") or "Kế hoạch tài chính"))
    st.markdown(
        f'<section class="p09-report-hero {status_class}">'
        '<div class="p09-report-eyebrow"><span>04 / BÁO CÁO</span><i>PERSONAL FINANCE REPORT</i></div>'
        '<div class="p09-report-hero-main"><div>'
        f'<h2>{goal_name}</h2><p>{int(calculation_result["goal_horizon_months"])} tháng · {escape(timing)}</p>'
        f'</div><strong>{status_label}</strong></div>'
        '<div class="p09-report-kpis">'
        f'<div><span>Mục tiêu cần đạt</span><b>{escape(money(goal))}</b><small>Đã tính theo giả định hiện tại</small></div>'
        f'<div><span>Giá trị dự kiến</span><b>{escape(money(projected))}</b><small>{progress:.0f}% mục tiêu</small></div>'
        f'<div><span>Cần dành mỗi tháng</span><b>{escape(money(calculation_result["required_monthly_contribution"]))}</b><small>Theo thời hạn đã chọn</small></div>'
        f'<div><span>Kết quả</span><b>{escape(result_label)}</b><small>Phương án cơ sở</small></div>'
        '</div></section>',
        unsafe_allow_html=True,
    )

    warning_messages = _report_warning_messages(calculation_result, validation_result)
    if warning_messages:
        warning_items = "".join("<li>" + escape(message) + "</li>" for message in warning_messages)
        st.markdown(
            '<section class="p09-report-notes"><div><span>!</span><strong>Điểm cần lưu ý</strong></div>'
            f'<ul>{warning_items}</ul></section>', unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="p09-report-section-head"><span>TỔNG QUAN TRỰC QUAN</span>'
        '<h3>Đọc nhanh kế hoạch trước khi xuất báo cáo</h3>'
        '<p>Hai biểu đồ dưới đây tóm tắt mức hoàn thành và chênh lệch giữa ba phương án.</p></div>',
        unsafe_allow_html=True,
    )
    with st.container(key="p09_report_charts"):
        left_chart, right_chart = st.columns(2, gap="large")
        with left_chart:
            st.plotly_chart(
                create_goal_progress_chart(base_scenario), width="stretch",
                key="report_goal_progress",
            )
        with right_chart:
            comparison_figure = create_final_value_chart(scenarios)
            comparison_figure.update_layout(height=350, margin={"l": 35, "r": 25, "t": 75, "b": 35})
            st.plotly_chart(comparison_figure, width="stretch", key="report_scenario_compare")

    with st.expander("Xem phân bổ dòng tiền và giả định của báo cáo", expanded=False):
        detail_chart, detail_table = st.columns([1.1, .9], gap="large")
        with detail_chart:
            st.plotly_chart(
                create_cashflow_chart(base_scenario), width="stretch",
                key="report_cashflow",
            )
        with detail_table:
            st.markdown("#### Các chỉ số dòng tiền")
            st.table({"Chỉ tiêu": ["Thu nhập / tháng", "Chi phí / tháng", "Dòng tiền dư / tháng", "Tỷ lệ tiết kiệm", "Vốn khả dụng"],
                      "Giá trị": [money(calculation_result["total_monthly_income"]), money(calculation_result["total_monthly_outflow"]),
                                  money(calculation_result["monthly_surplus"]), percent(calculation_result["savings_rate"]),
                                  money(calculation_result["initial_available_amount"])]})
        st.write("Lợi suất chỉ là giả định, không phải cam kết. Khoản dành cho mục tiêu được ghi nhận "
                 "vào cuối tháng; báo cáo chưa tính thuế và phí.")
        assumptions = calculation_result.get("assumptions_used", {})
        st.write("Lạm phát: " + ("Đã tính trong mô phỏng." if assumptions.get("inflation_enabled") else "Không điều chỉnh trong mô phỏng này."))

    explanation = st.session_state.get(PREFIX + "explanation")
    confirmed = bool(st.session_state.get(PREFIX + "report_confirmed"))
    pdf_bytes = st.session_state.get(PREFIX + "report_bytes")
    st.markdown(
        '<div class="p09-report-section-head"><span>HOÀN THIỆN BÁO CÁO</span>'
        '<h3>Ba bước để nhận bản PDF hoàn chỉnh</h3></div>'
        '<div class="p09-report-process">'
        f'<div class="{"is-done" if explanation else "is-active"}"><b>01</b><span>Tạo giải thích</span><small>Tóm tắt kế hoạch bằng ngôn ngữ dễ hiểu</small></div>'
        f'<div class="{"is-done" if confirmed else "is-active" if explanation else ""}"><b>02</b><span>Xác nhận nội dung</span><small>Đọc lại trước khi tạo tài liệu</small></div>'
        f'<div class="{"is-done" if pdf_bytes else "is-active" if confirmed else ""}"><b>03</b><span>Xem & tải báo cáo</span><small>PDF có biểu đồ và phông chữ nhúng</small></div>'
        '</div>', unsafe_allow_html=True,
    )

    explain_clicked = False
    use_llm = st.checkbox("Thêm nhận xét từ AI",
                          key=PREFIX + "use_llm", on_change=_invalidate)
    if use_llm:
        st.caption("Khi bấm Tạo phần giải thích, mục tiêu và kết quả tính toán được gửi đến OpenAI; có thể phát sinh chi phí. Không gửi ghi chú gốc.")
    else:
        st.caption("Giải thích dựa trên kết quả mô phỏng của bạn.")
    if not explanation:
        with st.container(key="p09_report_explain_action"):
            st.markdown(
                '<div class="p09-report-action-copy"><span>BƯỚC 01</span>'
                '<h3>Tạo phần giải thích cho kế hoạch</h3>'
                '<p>Hệ thống sẽ chuyển các kết quả thành nội dung ngắn gọn để bạn kiểm tra trước khi xuất PDF.</p></div>',
                unsafe_allow_html=True,
            )
            explain_clicked = st.button("Tạo phần giải thích", key=PREFIX + "explain", type="primary")
    if explain_clicked:
        try:
            result = generate_explanation_result(profile, calculation_result, scenario_result, validation_result, use_llm=use_llm)
            st.session_state[PREFIX + "explanation"] = result["text"]
            st.session_state[PREFIX + "explanation_meta"] = {key: value for key, value in result.items() if key != "text"}
            st.session_state.pop(PREFIX + "report_bytes", None)
            st.session_state[PREFIX + "report_confirmed"] = False
        except ExplanationError as exc:
            _invalidate()
            st.error(f"Chưa tạo được lời giải thích: {exc}")
    explanation = st.session_state.get(PREFIX + "explanation")
    if not explanation:
        return None

    meta = st.session_state.get(PREFIX + "explanation_meta", {})
    mode_label = {"offline": "Giải thích từ kết quả mô phỏng",
                  "fallback": "Dùng giải thích tiêu chuẩn · chưa có nhận xét AI",
                  "live_llm": "Có nhận xét bổ sung từ AI"}.get(meta.get("mode"), "Diễn giải đã kiểm tra")
    st.markdown('<span class="p09-badge">' + escape(mode_label) + '</span>', unsafe_allow_html=True)

    explanation_col, export_col = st.columns([1.55, .75], gap="large")
    with explanation_col:
        st.markdown('<div class="p09-report-card-title"><span>NỘI DUNG BÁO CÁO</span>'
                    '<h3>Giải thích kế hoạch</h3></div>', unsafe_allow_html=True)
        st.markdown('<div class="p09-explanation">' + _format_explanation_for_display(explanation) + '</div>',
                    unsafe_allow_html=True)
    with export_col:
        st.markdown(
            '<aside class="p09-report-export-card"><span>BẢN PDF BAO GỒM</span>'
            '<h3>Báo cáo của bạn</h3><ul>'
            '<li>Kết luận và bốn KPI chính</li><li>Biểu đồ tiến độ, dòng tiền, phương án</li>'
            '<li>So sánh phương án và kiểm tra rủi ro</li><li>Giải thích và lưu ý sử dụng</li>'
            '</ul><p>Thông thường 3 trang. Nội dung dài tự chuyển trang, không cắt mất lưu ý.</p></aside>', unsafe_allow_html=True,
        )
        confirmed = st.checkbox("Tôi đã đọc và xác nhận nội dung",
                                key=PREFIX + "report_confirmed")
    if not confirmed:
        st.session_state.pop(PREFIX + "report_bytes", None)
        return None
    if st.button("Tạo bản PDF hoàn chỉnh", key=PREFIX + "create_pdf", type="primary"):
        try:
            with tempfile.TemporaryDirectory(prefix="project09_person5_") as folder:
                path = str(Path(folder) / "project09_plan.pdf")
                generate_report(profile, {
                    "calculation_result": calculation_result,
                    "scenario_result": scenario_result,
                    "validation_result": validation_result,
                    "profile_confirmed": profile_confirmed,
                    "assumptions_confirmed": assumptions_confirmed,
                    "report_confirmed": True,
                }, explanation, path)
                st.session_state[PREFIX + "report_bytes"] = Path(path).read_bytes()
                st.session_state[PREFIX + "generated_at"] = datetime.now(
                    ZoneInfo("Asia/Ho_Chi_Minh")
                ).strftime("%d/%m/%Y · %H:%M")
        except (ReportError, OSError) as exc:
            st.session_state.pop(PREFIX + "report_bytes", None)
            st.error(f"Chưa tạo được PDF: {exc}")
    pdf_bytes = st.session_state.get(PREFIX + "report_bytes")
    if not pdf_bytes:
        return None
    page_count = len(PdfReader(BytesIO(pdf_bytes)).pages)
    st.markdown(
        '<section class="p09-report-ready"><div><span>✓</span><div><strong>Báo cáo đã sẵn sàng</strong>'
        f'<p>Tạo lúc {escape(st.session_state.get(PREFIX + "generated_at", "trong phiên hiện tại"))} · PDF {page_count} trang</p>'
        '</div></div><small>Bản báo cáo sử dụng dữ liệu và giả định của phiên hiện tại.</small></section>',
        unsafe_allow_html=True,
    )
    with st.container(key="p09_report_download"):
        st.download_button("Tải báo cáo PDF", data=pdf_bytes,
                           file_name="Project_09_Ke_hoach_tai_chinh.pdf",
                           mime="application/pdf", key=PREFIX + "download",
                           use_container_width=True)
    with st.expander("Xem trước đúng bản PDF vừa tạo", expanded=True):
        page_number = st.selectbox("Trang báo cáo", list(range(1, page_count + 1)), key=PREFIX + "preview_page")
        try:
            st.image(render_pdf_page(pdf_bytes, page_number - 1), caption=f"Trang {page_number}/{page_count} · bản PDF hiện tại", width="stretch")
        except (ImportError, OSError, ValueError):
            st.info("Không mở được xem trước. Bạn vẫn có thể tải bản PDF ở trên.")
    return {"explanation": explanation, "report_bytes": pdf_bytes,
            "report_confirmed": True, "source_fingerprint": signature}


def _standalone_demo() -> None:
    """Show a clearly labeled fixture when running this page in isolation."""
    import streamlit as st

    path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "p019_person5_demo.json"
    st.warning("DEMO ĐỘC LẬP: đây là tình huống minh họa đã được chuẩn bị sẵn, không phải dữ liệu của người dùng.")
    if not path.is_file():
        st.error("Không tìm thấy dữ liệu cho tình huống minh họa.")
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    profile_confirmed = st.checkbox("Tôi đã kiểm tra hồ sơ mẫu", key=PREFIX + "demo_profile")
    assumptions_confirmed = st.checkbox("Tôi xác nhận giả định mẫu", key=PREFIX + "demo_assumptions")
    render_report_page(payload["profile"], payload["calculation_result"],
                       payload["scenario_result"], payload["validation_result"],
                       profile_confirmed=profile_confirmed,
                       assumptions_confirmed=assumptions_confirmed)


if __name__ == "__main__":
    _standalone_demo()


__all__ = ["render_report_page"]
