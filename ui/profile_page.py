"""Streamlit profile-entry page for Project 09.

This module belongs to Person 1.  It collects a draft profile through either a
manual form or a natural-language text box.  It does not implement LLM calls,
business validation, profile confirmation, or financial calculations.

During independent development, natural-language extraction uses an exact
lookup against ``data/test_cases.json``.  At integration time, Person 4's
``extract_profile(text: str) -> dict`` function can be injected through the
``extractor`` argument of :func:`render_profile_page`.
"""

from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence, TypeAlias

import streamlit as st
from ui.readable import profile_summary_html
from ui.llm_panel import remember_origin
from pydantic import ValidationError

from src.schemas import PROFILE_FIELD_NAMES, parse_financial_profile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_CASES_PATH = PROJECT_ROOT / "data" / "test_cases.json"
PROFILE_DRAFT_SESSION_KEY = "profile_draft"
PROFILE_JUST_SAVED_SESSION_KEY = "profile_just_saved"

ProfileDict: TypeAlias = dict[str, Any]
ProfileExtractor: TypeAlias = Callable[[str], Mapping[str, Any]]

MONEY_FIELDS: tuple[str, ...] = (
    "monthly_primary_income",
    "monthly_other_income",
    "monthly_essential_expense",
    "monthly_discretionary_expense",
    "monthly_debt_payment",
    "current_savings",
    "emergency_fund_reserved",
    "goal_amount",
)

_NUMBER_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")


class MockExtractionError(ValueError):
    """Raised when text cannot be resolved by the deterministic mock extractor."""


def _has_meaningful_profile_data(profile: Mapping[str, Any]) -> bool:
    """Reject an all-empty extraction before it can replace the current draft."""
    return any(
        profile.get(field) is not None
        for field in PROFILE_FIELD_NAMES
        if field not in {"user_id", "notes"}
    )


def _normalise_whitespace(text: str) -> str:
    """Collapse repeated whitespace for deterministic fixture matching."""

    return " ".join(text.split())


def parse_optional_number_input(raw_value: str | None) -> float | None:
    """Convert a manual numeric field to a finite number or ``None``.

    Args:
        raw_value: Text entered by the user. An empty value means unknown.

    Returns:
        A float or ``None``. Negative numbers are preserved for Person 4's
        business-validation module.

    Raises:
        ValueError: If the value contains separators, is not numeric, or is not
            finite.
    """

    if raw_value is None or not raw_value.strip():
        return None

    cleaned = raw_value.strip()
    if not _NUMBER_PATTERN.fullmatch(cleaned):
        raise ValueError(
            "Giá trị số phải dùng chữ số, không dùng dấu phân cách hàng nghìn."
        )

    parsed = float(cleaned)
    if not math.isfinite(parsed):
        raise ValueError("Giá trị số phải hữu hạn.")
    return parsed


def parse_optional_integer_input(raw_value: str | None) -> int | None:
    """Convert a manual month field to an integer or ``None``.

    Args:
        raw_value: Text entered by the user. An empty value means unknown.

    Returns:
        An integer month count or ``None``.

    Raises:
        ValueError: If the value is not an integer.
    """

    if raw_value is None or not raw_value.strip():
        return None

    cleaned = raw_value.strip()
    if not _INTEGER_PATTERN.fullmatch(cleaned):
        raise ValueError("Thời hạn mục tiêu phải là số tháng nguyên.")
    return int(cleaned)


def _parse_optional_text(raw_value: str | None) -> str | None:
    """Strip a text field and convert an empty value to ``None``."""

    if raw_value is None:
        return None
    cleaned = raw_value.strip()
    return cleaned or None


def build_manual_profile(form_values: Mapping[str, str | None]) -> ProfileDict:
    """Build a canonical profile dictionary from manual-form strings.

    Args:
        form_values: Mapping that may contain the 15 canonical profile keys.
            Missing form values are treated as blank and converted to ``None``.

    Returns:
        A new JSON-compatible dictionary containing exactly the 15 shared keys.

    Raises:
        TypeError: If ``form_values`` is not a mapping.
        ValueError: If a numeric or month field cannot be parsed.
        pydantic.ValidationError: If an enum or structural field violates the
            shared schema.
    """

    if not isinstance(form_values, Mapping):
        raise TypeError("form_values must be a mapping")

    profile: ProfileDict = {field: None for field in PROFILE_FIELD_NAMES}
    for field in MONEY_FIELDS:
        profile[field] = parse_optional_number_input(form_values.get(field))

    profile["goal_horizon_months"] = parse_optional_integer_input(
        form_values.get("goal_horizon_months")
    )
    profile["expected_income_growth"] = parse_optional_number_input(
        form_values.get("expected_income_growth")
    )

    for field in ("user_id", "goal_name", "notes"):
        profile[field] = _parse_optional_text(form_values.get(field))

    for field in ("risk_tolerance", "liquidity_need"):
        profile[field] = _parse_optional_text(form_values.get(field))

    return parse_financial_profile(profile).to_profile_dict()


def load_mock_cases(path: Path | str = DEFAULT_TEST_CASES_PATH) -> list[dict[str, Any]]:
    """Load and structurally verify the synthetic extraction cases.

    Args:
        path: UTF-8 JSON file that contains a top-level ``cases`` list.

    Returns:
        A newly allocated list of mock cases.

    Raises:
        FileNotFoundError: If the fixture file does not exist.
        ValueError: If the JSON shape or a case is invalid.
    """

    fixture_path = Path(path)
    with fixture_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ValueError("test_cases.json must contain a non-empty cases list")

    verified_cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("each mock case must be an object")

        case_id = case.get("case_id")
        input_text = case.get("input_text")
        expected_profile = case.get("expected_profile")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("each mock case must have a non-empty case_id")
        if case_id in seen_ids:
            raise ValueError(f"duplicate mock case_id: {case_id}")
        if not isinstance(input_text, str) or not input_text.strip():
            raise ValueError(f"mock case {case_id} has no input_text")
        if not isinstance(expected_profile, Mapping):
            raise ValueError(f"mock case {case_id} has no expected_profile")

        canonical_profile = parse_financial_profile(expected_profile).to_profile_dict()
        verified = deepcopy(case)
        verified["expected_profile"] = canonical_profile
        verified_cases.append(verified)
        seen_ids.add(case_id)

    return verified_cases


def mock_extract_profile(
    text: str,
    cases: Sequence[Mapping[str, Any]] | None = None,
) -> ProfileDict:
    """Return fixture ground truth for an exact synthetic input-text match.

    This function is deliberately not an NLP extractor. It only lets other
    modules develop and demo against deterministic data before Person 4's LLM
    module is available.

    Args:
        text: Natural-language input to match.
        cases: Optional preloaded cases. When omitted, the shared JSON fixture
            is loaded from disk.

    Returns:
        A new canonical profile dictionary.

    Raises:
        MockExtractionError: If ``text`` is empty or not one of the fixtures.
        ValueError: If supplied mock cases are malformed.
    """

    if not isinstance(text, str) or not text.strip():
        raise MockExtractionError("Vui lòng nhập mô tả tài chính.")

    available_cases = list(cases) if cases is not None else load_mock_cases()
    normalised_input = _normalise_whitespace(text)
    for case in available_cases:
        candidate_text = case.get("input_text")
        expected_profile = case.get("expected_profile")
        if not isinstance(candidate_text, str) or not isinstance(
            expected_profile, Mapping
        ):
            raise ValueError("mock cases must contain input_text and expected_profile")
        if _normalise_whitespace(candidate_text) == normalised_input:
            return parse_financial_profile(expected_profile).to_profile_dict()

    raise MockExtractionError(
        "Tình huống mẫu đã bị thay đổi. Hãy chọn lại mẫu hoặc chuyển sang nhập thủ công."
    )


def _manual_form_values() -> tuple[bool, dict[str, str | None]]:
    """Render the institutional profile form and return its submitted values."""

    draft = st.session_state.get("person4_edited_profile") or st.session_state.get(PROFILE_DRAFT_SESSION_KEY, {})
    signature = json.dumps(draft, sort_keys=True, ensure_ascii=False)
    if st.session_state.get("profile_editor_seed") != signature:
        for field in PROFILE_FIELD_NAMES:
            value = draft.get(field)
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            st.session_state["profile_input_" + field] = (value if field in {"risk_tolerance", "liquidity_need"}
                else "" if value is None else str(value))
        st.session_state["profile_editor_seed"] = signature
    def text_input(field, label, **kwargs):
        return st.text_input(label, key="profile_input_" + field, **kwargs)

    with st.form("manual_profile_form"):
        values: dict[str, str | None] = {}
        st.markdown(
            '<div class="p09-form-brand"><div class="p09-form-mark">◈</div>'
            '<div><strong>PROJECT 09</strong><span>FINANCIAL PLANNING PROFILE</span></div>'
            '<small>HỒ SƠ KẾ HOẠCH TÀI CHÍNH</small></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="p09-form-section"><b>01</b><div><strong>Mục tiêu của bạn</strong>'
                    '<span>MỘT MỤC TIÊU, MỘT KẾ HOẠCH</span></div></div>', unsafe_allow_html=True)
        values["goal_name"] = text_input("goal_name", "Bạn muốn dành tiền cho việc gì?", placeholder="Ví dụ: Học cao học")
        left, right = st.columns(2)
        with left:
            values["goal_amount"] = text_input("goal_amount", "Giá trị theo giá hôm nay (VND)", placeholder="Ví dụ: 100000000",
                help="Hệ thống điều chỉnh số tiền này theo lạm phát. Nếu đã là số tiền cố định tại thời hạn, hãy đặt lạm phát = 0 ở Kế hoạch.")
        with right:
            values["goal_horizon_months"] = text_input("goal_horizon_months", "Bạn muốn đạt sau bao nhiêu tháng?", placeholder="Ví dụ: 36")
        st.markdown('<div class="p09-form-section"><b>02</b><div><strong>Dòng tiền hằng tháng</strong>'
                    '<span>MONTHLY CASH FLOW</span></div></div>', unsafe_allow_html=True)
        st.caption("Tiền tính bằng VND, nhập chữ số không có dấu phân cách. Nhập 0 nếu không có; để trống nếu chưa biết.")
        left, right = st.columns(2, gap="large")
        with left:
            values["monthly_primary_income"] = text_input("monthly_primary_income", "Thu nhập chính mỗi tháng (VND)", placeholder="Ví dụ: 10000000")
            values["monthly_essential_expense"] = text_input("monthly_essential_expense", "Chi phí thiết yếu mỗi tháng (VND)", placeholder="Ví dụ: 5000000")
            values["monthly_debt_payment"] = text_input("monthly_debt_payment", "Khoản trả nợ mỗi tháng (VND)", placeholder="Nhập 0 nếu không có")
        with right:
            values["monthly_other_income"] = text_input("monthly_other_income", "Thu nhập phụ mỗi tháng (VND)", placeholder="Nhập 0 nếu không có")
            values["monthly_discretionary_expense"] = text_input("monthly_discretionary_expense", "Chi phí không thiết yếu mỗi tháng (VND)", placeholder="Ví dụ: 2000000")
        st.markdown('<div class="p09-form-section"><b>03</b><div><strong>Tiết kiệm & dự phòng</strong>'
                    '<span>SAVINGS & EMERGENCY RESERVE</span></div></div>', unsafe_allow_html=True)
        left, right = st.columns(2, gap="large")
        with left:
            values["current_savings"] = text_input("current_savings", "Tiền tiết kiệm hiện có (VND)", placeholder="Ví dụ: 50000000")
        with right:
            values["emergency_fund_reserved"] = text_input("emergency_fund_reserved",
                "Quỹ dự phòng cần giữ lại (VND)", placeholder="Ví dụ: 15000000",
                help="Không tính khoản này vào vốn khả dụng cho mục tiêu.")
        st.markdown('<div class="p09-form-section"><b>04</b><div><strong>Ưu tiên của bạn</strong>'
                    '<span>RISK PREFERENCE</span></div></div>', unsafe_allow_html=True)
        choices = [None, "low", "medium", "high"]
        label_choice = lambda value: "Chưa cung cấp" if value is None else {"low": "Thấp", "medium": "Trung bình", "high": "Cao"}[value]
        left, right = st.columns(2)
        with left:
            values["risk_tolerance"] = st.selectbox(
                "Bạn chấp nhận mức biến động nào?", choices, format_func=label_choice,
                key="profile_input_risk_tolerance",
                help="Giới hạn lợi suất mô phỏng; không phải bài đánh giá đầu tư cá nhân.")
        with right:
            values["liquidity_need"] = st.selectbox(
                "Mức độ cần rút tiền sớm", choices, format_func=label_choice,
                key="profile_input_liquidity_need",
                help="Ghi nhận bối cảnh; chưa làm thay đổi phép tính hoặc mô phỏng rút tiền.")
        with st.expander("Thông tin bổ sung · Không bắt buộc", expanded=False):
            values["user_id"] = text_input("user_id", "Tên hoặc mã hồ sơ", help="Không nhập số giấy tờ cá nhân.")
            values["expected_income_growth"] = text_input("expected_income_growth",
                "Tăng thu nhập dự kiến · chỉ ghi nhận, chưa áp dụng", placeholder="Ví dụ: 0.05 tương đương 5%")
            values["notes"] = st.text_area(
                "Điều kiện hoặc lưu ý khác", height=90,
                key="profile_input_notes",
                placeholder="Ví dụ: Tôi không muốn sử dụng quỹ dự phòng...")
        submitted = st.form_submit_button("Lưu và kiểm tra thông tin →", type="primary", width="stretch")
    return submitted, values


def _render_natural_input(extractor: ProfileExtractor | None, choose_source: bool = False) -> ProfileDict | None:
    """Render natural-language input and return a submitted profile if available."""

    try:
        mock_cases = load_mock_cases()
    except (OSError, ValueError, ValidationError, json.JSONDecodeError):
        st.error("Không thể tải hồ sơ mẫu. Bạn có thể nhập thủ công.")
        return None

    if choose_source:
        source = st.radio("Cách tạo hồ sơ", ["Dữ liệu mẫu", "AI trực tuyến"], horizontal=True, key="profile_source")
        if source == "Dữ liệu mẫu":
            extractor = None
    if extractor is None:
        st.info("Hồ sơ mẫu có bản nháp sẵn. Để dùng thông tin riêng, chọn Nhập thủ công hoặc AI trực tuyến.")
    selected_case = st.selectbox(
        "Chọn tình huống mẫu",
        options=mock_cases,
        format_func=lambda case: f"{case['case_id']} — {case['expected_profile'].get('goal_name') or 'Kế hoạch tài chính'}",
    )
    input_text = st.text_area(
        "Mô tả tình hình tài chính",
        value=selected_case["input_text"],
        height=180,
        key=f"natural_input_{selected_case['case_id']}",
    )

    consent = True
    if extractor is not None and choose_source:
        consent = st.checkbox("Tôi đồng ý gửi mô tả này đến OpenAI để tạo bản nháp", key="profile_ai_consent")
        st.caption("AI trực tuyến có thể phát sinh chi phí. Chỉ xử lý khi bạn bấm Trích xuất hồ sơ.")
    if not st.button("Trích xuất hồ sơ", disabled=not consent, type="primary"):
        return None

    extraction_function: ProfileExtractor
    if extractor is None:
        extraction_function = lambda text: mock_extract_profile(text, mock_cases)
        st.info("Bạn đang dùng hồ sơ mẫu.")
    else:
        extraction_function = extractor

    try:
        extracted = extraction_function(input_text)
        profile = parse_financial_profile(extracted).to_profile_dict()
        if not _has_meaningful_profile_data(profile):
            st.error(
                "AI chưa nhận diện được thông tin tài chính hữu ích nên hồ sơ chưa được lưu. "
                "Hãy nêu rõ thu nhập, chi phí, tiết kiệm và mục tiêu hoặc chuyển sang nhập thủ công."
            )
            return None
        # An injected extractor may already have saved exact evidence separately.
        origin = st.session_state.get("profile_origin", {})
        if extractor is None:
            remember_origin("demo", profile, input_text)
        elif origin.get("profile") != profile or origin.get("text") != input_text:
            remember_origin("live_llm", profile, input_text)
        return profile
    except (MockExtractionError, TypeError, ValueError, ValidationError):
        st.error(
            "Chưa thể đọc đủ thông tin từ mô tả này. "
            "Hãy kiểm tra dữ liệu hoặc bổ sung thông tin."
        )
        return None
    except Exception as exc:
        # The injected extractor can be an external API. Keep the page alive and
        # avoid exposing credentials or provider error payloads to the user.
        safe_code = getattr(exc, "code", None)
        if safe_code == "api_key_missing":
            st.error("Tính năng AI chưa được thiết lập. Hãy chuyển sang nhập thủ công hoặc dùng tình huống mẫu.")
        elif safe_code in {"api_unavailable", "api_auth_failed", "api_permission_denied",
                           "api_model_not_found", "api_quota_exceeded", "api_request_invalid",
                           "api_service_unavailable", "api_timeout", "api_connection_failed",
                           "incomplete_output", "model_refusal",
                           "invalid_output", "ungrounded_output", "empty_extraction",
                           "wrong_provider_key", "out_of_scope",
                           "human_review_required"}:
            st.error(str(exc))
        else:
            st.error("Dịch vụ trích xuất tạm thời không khả dụng. Hãy dùng form thủ công.")
        return None


def render_profile_page(extractor: ProfileExtractor | None = None, *, choose_source: bool = False) -> ProfileDict | None:
    """Render Person 1's profile page and return the current draft profile.

    Args:
        extractor: Optional implementation of the shared
            ``extract_profile(text: str) -> dict`` contract. When omitted, the
            page uses deterministic fixture lookup.

    Returns:
        A new canonical profile dictionary after successful submission. If no
        new form is submitted, returns the existing draft from session state or
        ``None``.

    Raises:
        No expected application-level errors; user-input and extractor errors
        are displayed without terminating the Streamlit app.
    """

    with st.container(key="p09_accessible_profile_title"):
        st.header("Hồ sơ tài chính")
    st.markdown('<div class="p09-form-intro"><span>01 / THÔNG TIN CỦA BẠN</span>'
                '<h2>Cho chúng tôi biết mục tiêu của bạn</h2>'
                '<p>Nhập các thông tin cơ bản. Bạn luôn có thể kiểm tra và sửa ở bước tiếp theo.</p></div>',
                unsafe_allow_html=True)

    mode = st.radio(
        "Cách nhập dữ liệu",
        options=("Nhập thủ công", "Mô tả tự nhiên"),
        horizontal=True,
    )

    profile: ProfileDict | None = None
    if mode == "Nhập thủ công":
        form_col, guide_col = st.columns([2.3, 1], gap="large")
        with guide_col:
            st.markdown('<aside class="p09-guide"><span>HỒ SƠ CỦA BẠN</span><h3>Một kế hoạch bắt đầu từ những con số rõ ràng.</h3>'
                        '<h4>01 · Chọn mục tiêu</h4><p>Nhập giá trị theo giá hôm nay và thời hạn bạn mong muốn.</p>'
                        '<h4>02 · Hiểu dòng tiền</h4><p>Nhập khoản thu, chi và tiền dự phòng. Không có khoản nào thì ghi 0.</p>'
                        '<h4>03 · Kiểm tra lại</h4><p>Bạn có thể sửa toàn bộ dữ liệu trước khi lập kế hoạch.</p>'
                        '<hr><p>Kế hoạch sử dụng thu nhập hiện tại. Nhu cầu rút tiền và tăng thu nhập được lưu để tham khảo.</p></aside>', unsafe_allow_html=True)
        with form_col:
            submitted, values = _manual_form_values()
        if submitted:
            try:
                profile = build_manual_profile(values)
                remember_origin("manual", profile)
            except (TypeError, ValueError, ValidationError):
                st.error(
                    "Dữ liệu chưa đúng định dạng. Tiền dùng chữ số không có dấu "
                    "phân cách; thời hạn dùng số tháng nguyên."
                )
    else:
        profile = _render_natural_input(extractor, choose_source)

    if profile is not None:
        st.session_state[PROFILE_DRAFT_SESSION_KEY] = deepcopy(profile)
        st.session_state[PROFILE_JUST_SAVED_SESSION_KEY] = True
        st.success("Đã lưu hồ sơ. Đang chuyển sang bước Kiểm tra dữ liệu…")

    current_draft = st.session_state.get(PROFILE_DRAFT_SESSION_KEY)
    if isinstance(current_draft, Mapping):
        try:
            canonical_draft = parse_financial_profile(current_draft).to_profile_dict()
        except (TypeError, ValueError, ValidationError):
            st.error("Hồ sơ tạm thời không đúng định dạng. Hãy nhập lại thông tin.")
            return None
        with st.expander("Xem bản nháp đã lưu", expanded=False):
            st.markdown(profile_summary_html(canonical_draft), unsafe_allow_html=True)
        return deepcopy(canonical_draft)
    return None


if __name__ == "__main__":
    render_profile_page()


__all__ = [
    "DEFAULT_TEST_CASES_PATH",
    "MONEY_FIELDS",
    "MockExtractionError",
    "PROFILE_DRAFT_SESSION_KEY",
    "PROFILE_JUST_SAVED_SESSION_KEY",
    "ProfileExtractor",
    "build_manual_profile",
    "load_mock_cases",
    "mock_extract_profile",
    "parse_optional_integer_input",
    "parse_optional_number_input",
    "render_profile_page",
]
