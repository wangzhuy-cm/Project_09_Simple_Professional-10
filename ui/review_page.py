"""Person 4 review UI. Importable callback or standalone Streamlit entry point.

No shared app.py, form_page, calculation, scenario, explanation or report code
is implemented here. Only person4_* session keys are written. A returned bundle
is a confirmed simulation input, never a final plan.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from html import escape
import json
import math
from pathlib import Path
import re
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.llm_extraction import (ExtractionError, extract_profile, extract_mock_profile,
                                load_demo_cases, generate_clarification_questions,
                                get_openai_status)
from src.schemas import PROFILE_FIELD_NAMES
from src.goal_review import build_goal_review
from src.validation import validate_profile
from ui.theme import money
from ui.llm_panel import render_origin

PREFIX = "person4_"
TEXT_FIELDS = {"user_id", "goal_name", "notes"}
ENUM_FIELDS = {"risk_tolerance", "liquidity_need"}
LABELS = {
    "user_id": "Mã hồ sơ tùy chọn (không nhập số giấy tờ cá nhân)",
    "monthly_primary_income": "Thu nhập chính / tháng (VND)",
    "monthly_other_income": "Thu nhập phụ / tháng (VND)",
    "monthly_essential_expense": "Chi phí thiết yếu / tháng (VND)",
    "monthly_discretionary_expense": "Chi phí không thiết yếu / tháng (VND)",
    "monthly_debt_payment": "Trả nợ / tháng (VND)",
    "current_savings": "Tiết kiệm hiện có (VND)",
    "emergency_fund_reserved": "Quỹ dự phòng giữ lại (VND)",
    "goal_name": "Một mục tiêu chính",
    "goal_amount": "Giá trị mục tiêu theo giá hôm nay (VND)",
    "goal_horizon_months": "Thời hạn mục tiêu (số tháng nguyên)",
    "risk_tolerance": "Mức chấp nhận rủi ro",
    "liquidity_need": "Nhu cầu rút tiền sớm · chỉ ghi nhận",
    "expected_income_growth": "Tăng thu nhập / năm · chưa áp dụng (0.05 = 5%)",
    "notes": "Ghi chú / nguyên văn mô tả để kiểm tra ý định",
}
ASSUMPTION_LABELS = {
    "annual_return_rate": "Lợi suất giả định / năm (thập phân, bắt buộc)",
    "annual_inflation_rate": "Lạm phát giả định / năm (thập phân, có thể để trống)",
    "monthly_contribution": "Đóng góp / tháng (VND, trống = tự động)",
    "max_projection_months": "Giới hạn dự phóng (tháng nguyên, có thể để trống)",
}


def _fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def parse_manual_fields(raw_profile: dict, raw_assumptions: dict) -> tuple[dict, dict, list[str]]:
    """UI text -> contract values; never coerce bad text to zero or silently omit it.

    Use plain digits, optional decimal dot, no thousands separator/exponents.
    Empty optional assumptions are omitted to use the engine's documented
    defaults; empty profile fields always remain None.
    """
    errors = []

    def number(field, raw, integer=False):
        if raw is None or raw == "":
            return None
        if not isinstance(raw, str):
            errors.append(f"{field}: cần nhập số bằng chữ số.")
            return None
        value = raw.strip()
        if not value:
            return None
        pattern = r"[+-]?\d+" if integer else r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
        try:
            if not re.fullmatch(pattern, value):
                raise ValueError
            parsed = int(value) if integer else float(value)
            if not math.isfinite(parsed):
                raise ValueError
            return parsed
        except (ValueError, OverflowError):
            errors.append(f"{field}: dùng số {'nguyên' if integer else 'hữu hạn'}, dấu chấm thập phân; không dùng dấu phân cách hàng nghìn.")
            return None

    profile = {}
    for field in PROFILE_FIELD_NAMES:
        raw = raw_profile.get(field)
        if field in TEXT_FIELDS:
            if raw is not None and not isinstance(raw, str):
                errors.append(f"{field}: cần nhập văn bản.")
                profile[field] = None
            else:
                profile[field] = raw.strip() if raw and raw.strip() else None
        elif field in ENUM_FIELDS:
            if raw not in (None, "low", "medium", "high"):
                errors.append(f"{field}: chọn low, medium hoặc high.")
                raw = None
            profile[field] = raw
        else:
            profile[field] = number(field, raw, field == "goal_horizon_months")
    assumptions = {}
    for field in ASSUMPTION_LABELS:
        value = number("assumptions." + field, raw_assumptions.get(field), field == "max_projection_months")
        if value is not None:
            assumptions[field] = value
    return profile, assumptions, errors


def build_review_bundle(profile: dict, assumptions: dict, profile_confirmed: bool,
                        assumptions_confirmed: bool, input_errors: list | None = None) -> dict | None:
    """Revalidate at the boundary; never trust caller-supplied validation flags."""
    result = validate_profile(profile, assumptions)
    if input_errors or not result["can_simulate"] or profile_confirmed is not True or assumptions_confirmed is not True:
        return None
    return {"profile": deepcopy(profile), "assumptions": deepcopy(assumptions),
            "validation_result": result, "profile_confirmed": True,
            "assumptions_confirmed": True, "ready_for_simulation": True, "is_final_plan": False}


def _invalidate():
    st.session_state[PREFIX + "profile_confirmed"] = False
    st.session_state[PREFIX + "assumptions_confirmed"] = False
    st.session_state[PREFIX + "result"] = None
    st.session_state.pop(PREFIX + "ai_questions", None)


def _text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _seed(profile=None, assumptions=None):
    _invalidate()
    for field in PROFILE_FIELD_NAMES:
        value = profile.get(field) if isinstance(profile, dict) else None
        st.session_state[PREFIX + field] = value if field in ENUM_FIELDS and value in (None, "low", "medium", "high") else (None if field in ENUM_FIELDS else _text(value))
    for field in ASSUMPTION_LABELS:
        value = assumptions.get(field) if isinstance(assumptions, dict) else None
        st.session_state[PREFIX + "a_" + field] = _text(value)


def _reset():
    # Remove this module's keys only; upstream profile_draft and other members'
    # session data are intentionally not part of this namespace.
    for key in list(st.session_state):
        if key.startswith(PREFIX):
            del st.session_state[key]


def _load_sample_callback(cases_by_id: dict, assumptions: dict | None) -> None:
    """Load a fixture before Streamlit recreates widgets on the next rerun."""
    case_id = st.session_state.get(PREFIX + "sample")
    source = cases_by_id.get(case_id, {}).get("input_text")
    if not isinstance(source, str):
        st.session_state[PREFIX + "extraction_error"] = "Không tìm thấy tình huống mẫu đã chọn."
        return
    try:
        _seed(extract_mock_profile(source), assumptions)
        st.session_state[PREFIX + "raw_text"] = source
        st.session_state[PREFIX + "source"] = "Tình huống mẫu ngoại tuyến."
        st.session_state.pop(PREFIX + "extraction_error", None)
    except ExtractionError as exc:
        st.session_state[PREFIX + "extraction_error"] = str(exc)


def _extract_ai_callback(assumptions: dict | None) -> None:
    """Extract into widget state from a callback, before widget instantiation."""
    _invalidate()
    text = str(st.session_state.get(PREFIX + "raw_text", ""))
    try:
        _seed(extract_profile(text), assumptions)
        st.session_state[PREFIX + "source"] = "Bản nháp từ AI; cần người dùng kiểm tra."
        st.session_state.pop(PREFIX + "extraction_error", None)
    except ExtractionError as exc:
        st.session_state[PREFIX + "extraction_error"] = f"{exc.code}: {exc}"


def render_review_page(profile: dict | None = None, assumptions: dict | None = None) -> dict | None:
    """Render review and return a fresh confirmed bundle or None on EVERY rerun.

    Caller must replace/clear any previously cached bundle when None is returned.
    Incoming values are drafts; changes reset both confirmations. Never treat
    validate_profile(...).can_simulate as human approval by itself.
    """
    upstream = _fingerprint([profile, assumptions])
    if st.session_state.get(PREFIX + "upstream") != upstream:
        _seed(profile, assumptions)
        st.session_state[PREFIX + "upstream"] = upstream
        st.session_state[PREFIX + "raw_text"] = ""
        st.session_state.pop(PREFIX + "extraction_error", None)

    with st.container(key="p09_accessible_review_title"):
        st.header("Kiểm tra thông tin")
    st.markdown('<div class="p09-form-intro"><span>02 / KIỂM TRA THÔNG TIN</span>'
                '<h2>Đây là những gì chúng tôi đã hiểu</h2>'
                '<p>Hãy kiểm tra các con số chính. Nếu có gì chưa đúng, bạn có thể sửa trước khi xem kế hoạch.</p></div>',
                unsafe_allow_html=True)

    current_raw = {f: st.session_state.get(PREFIX + f) for f in PROFILE_FIELD_NAMES}
    current_assumptions = {f: st.session_state.get(PREFIX + "a_" + f) for f in ASSUMPTION_LABELS}
    preview, _, _ = parse_manual_fields(current_raw, current_assumptions)
    income_values = [preview.get(name) for name in ("monthly_primary_income", "monthly_other_income")]
    outflow_values = [preview.get(name) for name in (
        "monthly_essential_expense", "monthly_discretionary_expense", "monthly_debt_payment")]
    total_income = None if any(value is None for value in income_values) else sum(income_values)
    total_outflow = None if any(value is None for value in outflow_values) else sum(outflow_values)
    savings = preview.get("current_savings")
    reserved = preview.get("emergency_fund_reserved")
    available = None if savings is None or reserved is None else max(0, savings - reserved)
    remaining = None if total_income is None or total_outflow is None else total_income - total_outflow
    risk = {"low": "Thấp", "medium": "Trung bình", "high": "Cao"}.get(
        preview.get("risk_tolerance"), "Chưa cung cấp")
    summary = (
        '<section class="p09-review-summary"><div class="p09-review-summary-head">'
        '<div><span>TÓM TẮT HỒ SƠ</span><h3>' + escape(str(preview.get("goal_name") or "Mục tiêu của bạn")) + '</h3></div>'
        '<strong>' + escape(str(preview.get("goal_horizon_months") or "—")) + ' tháng</strong></div>'
        '<div class="p09-review-grid">'
        f'<div><span>Tổng thu nhập</span><strong>{escape(money(total_income))}/tháng</strong></div>'
        f'<div><span>Tổng chi tiêu & trả nợ</span><strong>{escape(money(total_outflow))}/tháng</strong></div>'
        f'<div><span>Dòng tiền còn lại</span><strong>{escape(money(remaining))}/tháng</strong></div>'
        f'<div><span>Tiết kiệm có thể sử dụng</span><strong>{escape(money(available))}</strong></div>'
        f'<div><span>Số tiền mục tiêu</span><strong>{escape(money(preview.get("goal_amount")))}</strong></div>'
        f'<div><span>Mức chấp nhận rủi ro</span><strong>{escape(risk)}</strong></div>'
        '</div></section>'
    )
    st.markdown(summary, unsafe_allow_html=True)
    render_origin(preview)

    with st.expander("Sửa thông tin", expanded=False):
        st.caption("Chỉ sửa những mục chưa đúng. Tiền nhập bằng chữ số, ví dụ 8000000.")
        groups = {
            "monthly_primary_income": "Thu nhập & chi tiêu",
            "current_savings": "Tiết kiệm & dự phòng",
            "goal_name": "Mục tiêu",
            "risk_tolerance": "Mức phù hợp & ghi chú",
        }
        cols = st.columns(2, gap="large")
        index = 0
        for field in PROFILE_FIELD_NAMES:
            if field in groups:
                st.markdown("#### " + groups[field])
                cols = st.columns(2, gap="large")
                index = 0
            key = PREFIX + field
            with cols[index % 2]:
                if field in ENUM_FIELDS:
                    st.selectbox(LABELS[field], [None, "low", "medium", "high"],
                                 format_func=lambda v: "Chưa cung cấp" if v is None else {
                                     "low": "Thấp", "medium": "Trung bình", "high": "Cao"}[v],
                                 key=key, on_change=_invalidate)
                elif field == "notes":
                    st.text_area(LABELS[field], key=key, on_change=_invalidate, height=90)
                else:
                    st.text_input(LABELS[field], key=key, on_change=_invalidate)
            index += 1

    with st.expander("Giả định nâng cao · Không bắt buộc", expanded=False):
        st.caption("Bạn có thể giữ nguyên các giá trị mặc định nếu chưa muốn tự điều chỉnh.")
        left, right = st.columns(2, gap="large")
        for i, (field, label) in enumerate(ASSUMPTION_LABELS.items()):
            with (left if i % 2 == 0 else right):
                st.text_input(label, key=PREFIX + "a_" + field, on_change=_invalidate)

    # Standalone module demos retain their test harness; integrated users use
    # the dedicated profile page instead of a second, confusing extraction UI.
    if profile is None:
        with st.expander("Thử tình huống khác · Công cụ minh họa", expanded=False):
            st.button("Khôi phục thông tin ban đầu", key=PREFIX + "reset", on_click=_reset)
            try:
                cases = load_demo_cases()
            except ExtractionError as exc:
                cases = []
                st.info(str(exc))
            if cases:
                by_id = {case["case_id"]: case for case in cases}
                st.selectbox("Tình huống mẫu", list(by_id), key=PREFIX + "sample")
                st.button("Tải tình huống mẫu", key=PREFIX + "load_sample",
                          on_click=_load_sample_callback, args=(by_id, assumptions))
            st.text_area("Mô tả bằng ngôn ngữ tự nhiên", key=PREFIX + "raw_text", on_change=_invalidate)
            api_ready = get_openai_status()["configured"]
            st.button("Đọc lại bằng OpenAI", key=PREFIX + "extract", disabled=not api_ready,
                      on_click=_extract_ai_callback, args=(assumptions,))
            if not api_ready:
                st.caption("Tính năng AI chưa được thiết lập; nhập thủ công và tình huống mẫu vẫn hoạt động bình thường.")
            if st.session_state.get(PREFIX + "extraction_error"):
                st.error(st.session_state[PREFIX + "extraction_error"])

    raw_profile = {f: st.session_state[PREFIX + f] for f in PROFILE_FIELD_NAMES}
    raw_assumptions = {f: st.session_state[PREFIX + "a_" + f] for f in ASSUMPTION_LABELS}
    edited, chosen, parse_errors = parse_manual_fields(raw_profile, raw_assumptions)
    st.session_state[PREFIX + "edited_profile"] = deepcopy(edited)
    result = validate_profile(edited, chosen)
    # An invalid optional numeric text must not look VALID after its parsing
    # result is omitted from assumptions. Keep the user-facing status honest.
    for message in parse_errors:
        result["errors"].append({"code": "manual_parse_error", "field": message.split(":", 1)[0], "message": message})
        result["clarification_questions"].append(message)
    if parse_errors:
        result["can_simulate"] = False
        if result["status"] not in {"OUT_OF_SCOPE", "HUMAN_REVIEW_REQUIRED"}:
            result["status"] = "NEEDS_CLARIFICATION"
    st.markdown("### Mục tiêu, nguồn lực và ràng buộc")
    st.caption("Tóm tắt từ thông tin bạn đã nhập để kiểm tra trước khi lập kế hoạch.")
    st.dataframe(build_goal_review(edited, result), width="stretch", hide_index=True)
    st.caption("Nếu thông tin chưa đúng hoặc còn thiếu, mở Sửa thông tin ở phía trên. "
               "Bảng cập nhật theo hồ sơ; bạn vẫn cần xác nhận trước khi mô phỏng.")
    rows = []
    problem_fields = {issue.get("field") for issue in result["errors"] if isinstance(issue, dict)}
    for field in PROFILE_FIELD_NAMES:
        value = edited[field]
        unit = "VND" if field in {"monthly_primary_income", "monthly_other_income", "monthly_essential_expense",
                                  "monthly_discretionary_expense", "monthly_debt_payment", "current_savings",
                                  "emergency_fund_reserved", "goal_amount"} else ("tháng" if field == "goal_horizon_months" else "")
        display = money(value) if unit == "VND" and value is not None else ("Chưa có dữ liệu" if value is None else str(value))
        rows.append({"Trường": LABELS[field], "Giá trị": display, "Đơn vị": unit,
                     "Trạng thái": "Cần sửa" if field in problem_fields else (
                         "Cần bổ sung" if field in result["missing_fields"] else ("Để trống" if value is None else "Đã nhập"))})
    with st.expander("Xem toàn bộ thông tin đã nhập", expanded=False):
        st.dataframe(rows, width="stretch", hide_index=True)
        status_text = {
            "VALID": "Đã đầy đủ",
            "WARNING": "Đã đầy đủ, có điểm cần lưu ý",
            "NEEDS_CLARIFICATION": "Cần bổ sung thông tin",
            "HUMAN_REVIEW_REQUIRED": "Cần kiểm tra lại",
            "OUT_OF_SCOPE": "Ngoài phạm vi lập kế hoạch",
        }.get(result["status"], "Đang kiểm tra")
        st.caption("Trạng thái: " + status_text)
    many_missing = len(result["missing_fields"]) >= 6
    for issue in result["errors"]:
        if many_missing and issue.get("code") == "missing_required_field":
            continue
        st.error(issue["message"])
    for issue in result["warnings"]:
        if issue.get("code") != "income_growth_not_applied_in_mvp":
            st.warning(issue["message"])
    if result["clarification_questions"]:
        if many_missing:
            st.warning(
                "Hồ sơ còn thiếu nhiều thông tin nên chưa thể lập kế hoạch. "
                "Hãy quay lại bước Hồ sơ, nhập lại bằng AI hoặc dùng biểu mẫu thủ công."
            )
            with st.expander("Xem các thông tin còn thiếu", expanded=False):
                for question in result["clarification_questions"]:
                    st.write("• " + question)
        else:
            st.markdown("#### Cần bổ sung trước khi tiếp tục")
            for question in result["clarification_questions"]:
                st.write("• " + question)
    elif result["can_simulate"]:
        st.success("Thông tin đã đầy đủ và có thể lập kế hoạch.")

    blocked = bool(parse_errors or st.session_state.get(PREFIX + "extraction_error") or not result["can_simulate"])
    if blocked:
        _invalidate()
    st.caption("Xác nhận này áp dụng cho hồ sơ. Bạn sẽ xem và xác nhận giả định cuối cùng ở trang Kế hoạch.")
    confirmed = st.checkbox("Tôi đã kiểm tra và xác nhận các thông tin trên là đúng",
                            key=PREFIX + "profile_confirmed", disabled=blocked)
    st.session_state[PREFIX + "assumptions_confirmed"] = confirmed
    bundle = build_review_bundle(edited, chosen, confirmed, confirmed,
                                 parse_errors or (["extraction_failed"] if st.session_state.get(PREFIX + "extraction_error") else []))
    st.session_state[PREFIX + "result"] = deepcopy(bundle)
    if bundle:
        st.success("Đã xác nhận. Kế hoạch của bạn đã sẵn sàng.")
    else:
        st.caption("Bạn cần xác nhận thông tin trước khi xem kế hoạch.")
    return deepcopy(bundle)


if __name__ == "__main__":
    render_review_page()


__all__ = ["render_review_page", "parse_manual_fields", "build_review_bundle"]
