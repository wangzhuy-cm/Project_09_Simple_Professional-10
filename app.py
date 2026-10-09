"""Integrated Streamlit workflow for Project 09.

The app composes the five owner modules without changing their public APIs.
It keeps only fresh, confirmed downstream bundles and revalidates the final
base assumptions selected on the scenario page before enabling reports.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from typing import Any

import streamlit as st

from src.llm_extraction import extract_profile_with_evidence
from src.market_reference import reference_assumptions
from src.validation import validate_profile
from ui.cashflow_page import render_cashflow_page
from ui.evaluation_panel import render_evaluation_panel
from ui.profile_page import (
    PROFILE_DRAFT_SESSION_KEY,
    PROFILE_JUST_SAVED_SESSION_KEY,
    render_profile_page,
)
from ui.report_page import render_report_page
from ui.review_page import render_review_page
from ui.scenario_page import render_scenario_page
from ui.theme import load_theme
from ui.llm_panel import remember_origin, render_llm_showcase


APP_PREFIX = "integrated_"
INITIAL_ASSUMPTIONS = reference_assumptions()


def _fingerprint(value: Any) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True,
                   allow_nan=False, default=str).encode("utf-8")
    ).hexdigest()


def _clear_after_profile() -> None:
    for key in (
        APP_PREFIX + "review_bundle",
        APP_PREFIX + "scenario_bundle",
        APP_PREFIX + "report_bundle",
    ):
        st.session_state.pop(key, None)


def _clear_after_review() -> None:
    for key in (APP_PREFIX + "scenario_bundle", APP_PREFIX + "report_bundle"):
        st.session_state.pop(key, None)


def _clear_after_scenario() -> None:
    st.session_state.pop(APP_PREFIX + "report_bundle", None)


def _sync_profile_draft() -> dict | None:
    draft = st.session_state.get(PROFILE_DRAFT_SESSION_KEY)
    if not isinstance(draft, dict):
        return None
    signature = _fingerprint(draft)
    if st.session_state.get(APP_PREFIX + "profile_signature") != signature:
        _clear_after_profile()
        st.session_state.pop("person4_edited_profile", None)
        st.session_state[APP_PREFIX + "profile_signature"] = signature
    return draft


def _status_panel() -> None:
    draft = _sync_profile_draft()
    reviewed = st.session_state.get(APP_PREFIX + "review_bundle")
    simulated = st.session_state.get(APP_PREFIX + "scenario_bundle")
    reported = st.session_state.get(APP_PREFIX + "report_bundle")
    st.caption("TIẾN ĐỘ PHIÊN HIỆN TẠI")
    items = (("01", "Thông tin đã nhập", draft), ("02", "Thông tin đã kiểm tra", reviewed),
             ("03", "Kế hoạch đã tạo", simulated), ("04", "Báo cáo PDF", reported))
    markup = "".join(f'<div class="p09-progress-row"><span class="p09-progress-num">{number}</span>'
                     f'<span>{label}</span><span class="p09-progress-state">{"✓" if ready else "·"}</span></div>'
                     for number, label, ready in items)
    st.markdown(f'<div class="p09-progress">{markup}</div>', unsafe_allow_html=True)
    if not reviewed and draft:
        st.caption("Hãy kiểm tra thông tin trước khi xem kế hoạch.")


def _new_session() -> None:
    # Every owner module keeps its own namespace; only the app's workflow keys
    # and the known owner UI state are reset after explicit confirmation.
    for key in list(st.session_state):
        if (str(key).startswith((APP_PREFIX, "person3_", "person4_", "person5_", "profile_", "natural_input_", "evaluation_"))
                or key in {PROFILE_DRAFT_SESSION_KEY, PROFILE_JUST_SAVED_SESSION_KEY}):
            st.session_state.pop(key, None)
    st.session_state[APP_PREFIX + "page"] = "Tổng quan"


def _overview() -> None:
    draft = _sync_profile_draft()
    with st.container(key="p09_home_hero"):
        with st.container(key="p09_overview_brand"):
            st.title("Project 09 - Goal-Based Personal Finance Planner")
        left, right = st.columns([1.45, 1], vertical_alignment="center")
        with left:
            st.markdown(
                '<div class="p09-hero-copy">'
                '<div class="p09-eyebrow"><span></span> PROJECT 09 — KẾ HOẠCH TÀI CHÍNH</div>'
                '<h1>Mục tiêu rõ ràng.<br><em>Kế hoạch dễ hiểu.</em></h1>'
                '<div class="p09-tagline">Nhập thông tin&nbsp; · &nbsp;Xem kế hoạch&nbsp; · &nbsp;Điều chỉnh khi cần</div>'
                '<p>Biến thu nhập, chi tiêu và mục tiêu của bạn thành một kế hoạch tiết kiệm '
                'dễ theo dõi — không cần kiến thức tài chính chuyên sâu.</p>'
                '</div>', unsafe_allow_html=True)
            target = ("3. Mô phỏng" if st.session_state.get(APP_PREFIX + "review_bundle")
                      else "2. Xác nhận") if draft else "1. Hồ sơ"
            st.button("Tiếp tục kế hoạch  ↗" if draft else "Bắt đầu lập kế hoạch  ↗",
                      type="primary", key="p09_hero_cta",
                      on_click=lambda: st.session_state.update({APP_PREFIX + "page": target}))
            st.markdown('<div class="p09-hero-note">Bắt đầu bằng thông tin của bạn hoặc một hồ sơ mẫu.</div>',
                        unsafe_allow_html=True)
        with right:
            st.markdown(
                '<div class="p09-hero-stats">'
                '<div><strong>04</strong><span>BƯỚC LẬP KẾ HOẠCH</span></div>'
                '<div><strong>03</strong><span>KỊCH BẢN SO SÁNH</span></div>'
                '<div><strong>01</strong><span>BÁO CÁO CỦA BẠN</span></div>'
                '</div>', unsafe_allow_html=True)
    with st.container(key="p09_home_after"):
        st.markdown('<div class="p09-section-kicker">QUY TRÌNH / 01—04</div>'
                    '<h2>Mọi quyết định bắt đầu từ dữ liệu của bạn.</h2>', unsafe_allow_html=True)
        st.markdown(
            '<div class="p09-process-grid">'
            '<article class="p09-process-card">'
            '<div class="p09-process-top"><span>01</span><i>↗</i></div>'
            '<div class="p09-process-icon"><svg viewBox="0 0 32 32" aria-hidden="true">'
            '<path d="M6 23V13m7 10V8m7 15V16m6 7V5"/><path d="m5 9 7-5 7 5 8-6"/></svg></div>'
            '<h3>Nhập thông tin</h3>'
            '<p>Cho chúng tôi biết thu nhập, chi tiêu và mục tiêu của bạn.</p>'
            '<div class="p09-process-meta">NHANH · RÕ · CÓ THỂ SỬA</div></article>'
            '<article class="p09-process-card">'
            '<div class="p09-process-top"><span>02</span><i>↗</i></div>'
            '<div class="p09-process-icon"><svg viewBox="0 0 32 32" aria-hidden="true">'
            '<path d="M5 8h22M5 16h22M5 24h22"/><circle cx="11" cy="8" r="2.5"/>'
            '<circle cx="21" cy="16" r="2.5"/><circle cx="14" cy="24" r="2.5"/></svg></div>'
            '<h3>Xem kế hoạch</h3>'
            '<p>Biết cần dành bao nhiêu mỗi tháng và khi nào có thể đạt mục tiêu.</p>'
            '<div class="p09-process-meta">KẾT QUẢ · BA PHƯƠNG ÁN</div></article>'
            '<article class="p09-process-card">'
            '<div class="p09-process-top"><span>03</span><i>↗</i></div>'
            '<div class="p09-process-icon"><svg viewBox="0 0 32 32" aria-hidden="true">'
            '<path d="M8 4h12l5 5v19H8z"/><path d="M20 4v6h5M12 15h9M12 20h9M12 25h6"/></svg></div>'
            '<h3>Điều chỉnh & lưu</h3>'
            '<p>Thử thay đổi kế hoạch, xem rủi ro và tải báo cáo PDF.</p>'
            '<div class="p09-process-meta">KẾT QUẢ · BÁO CÁO PDF</div></article>'
            '</div><div class="p09-process-note"><span>i</span>'
            'Mô phỏng phục vụ học tập, không thay thế tư vấn tài chính.</div>',
            unsafe_allow_html=True,
        )


def _top_navigation() -> None:
    pages = (("Tổng quan", "Trang chủ", ":material/home:"),
             ("1. Hồ sơ", "Hồ sơ", ":material/person:"),
             ("2. Xác nhận", "Xác nhận", ":material/fact_check:"),
             ("3. Mô phỏng", "Kế hoạch", ":material/show_chart:"),
             ("4. Báo cáo", "Báo cáo", ":material/description:"))
    current = st.session_state.get(APP_PREFIX + "page", "Tổng quan")
    with st.container(key="p09_top_nav"):
        brand, *links, tools_col = st.columns([2.7, 1.08, 1, 1.06, 1.14, 1, 1.14],
                                              vertical_alignment="center", gap="small")
        with brand:
            st.markdown('<div class="p09-brand"><span class="p09-brand-symbol">◈</span>'
                        '<span>PROJECT <b>09</b><small>GOAL-BASED FINANCE PLANNER</small></span></div>',
                        unsafe_allow_html=True)
        for col, (page, label, icon) in zip(links, pages):
            with col:
                st.button(label, key="p09_nav_" + page,
                          type="primary" if current == page else "secondary",
                          icon=icon,
                          on_click=lambda selected=page: st.session_state.update({APP_PREFIX + "page": selected}),
                          use_container_width=True)
        with tools_col:
            with st.popover("Tiến độ", icon=":material/checklist:", key="p09_progress_popover"):
                _status_panel()
                if st.checkbox("Tôi xác nhận bắt đầu phiên mới", key=APP_PREFIX + "reset_confirm"):
                    st.button("Xóa dữ liệu phiên này", key=APP_PREFIX + "reset", on_click=_new_session)


def _page_banner(page: str) -> None:
    title, accent, description = {
        "1. Hồ sơ": ("Nhập", "thông tin", "Chia sẻ dòng tiền và một mục tiêu bạn muốn đạt được."),
        "2. Xác nhận": ("Kiểm tra", "thông tin", "Xem lại những gì hệ thống đã hiểu trước khi lập kế hoạch."),
        "3. Mô phỏng": ("Kế hoạch", "của bạn", "Xem khả năng đạt mục tiêu và thử các phương án đơn giản."),
        "4. Báo cáo": ("Báo cáo", "của bạn", "Đọc lời giải thích và duyệt bản PDF cuối cùng."),
    }[page]
    steps = (("1", "Nhập thông tin"), ("2", "Kiểm tra"), ("3", "Kế hoạch"), ("4", "Báo cáo"))
    active = int(page[0])
    timeline = "".join(f'<span class="{"is-active" if int(n) == active else ""}">'
                       f'<b>{n}</b> {label}</span>' for n, label in steps)
    with st.container(key="p09_page_banner"):
        st.markdown(f'<div class="p09-banner-content"><div class="p09-banner-eyebrow">'
                    f'PROJECT 09 &nbsp;/&nbsp; BƯỚC {active:02d}</div>'
                    f'<h1>{title} <em>{accent}</em></h1><p>{description}</p>'
                    f'<div class="p09-stepper">{timeline}</div></div>', unsafe_allow_html=True)


def _page_actions(page: str) -> None:
    """Keep the previous step visible without competing with the main action."""
    actions = {
        "1. Hồ sơ": (("← Trang chủ", "Tổng quan", "p09_back_home"),),
        "2. Xác nhận": (("← Quay lại Nhập thông tin", "1. Hồ sơ", "p09_back_profile"),),
        "3. Mô phỏng": (("← Quay lại Kiểm tra", "2. Xác nhận", "p09_back_review"),),
        "4. Báo cáo": (
            ("← Quay lại Kế hoạch", "3. Mô phỏng", "p09_back_scenario"),
            ("Quay về Kiểm tra dữ liệu", "2. Xác nhận", "p09_report_back_review"),
        ),
    }[page]
    with st.container(key="p09_page_actions"):
        columns = st.columns([1.05, 1.1, 3.8] if len(actions) == 2 else [1.4, 4.6], gap="small")
        for column, (label, target, key) in zip(columns, actions):
            with column:
                st.button(
                    label,
                    key=key,
                    on_click=lambda destination=target: st.session_state.update(
                        {APP_PREFIX + "page": destination}
                    ),
                    use_container_width=True,
                )


def _extract_with_evidence(text: str) -> dict:
    result = extract_profile_with_evidence(text)
    remember_origin("live_llm", result["profile"], text, result["evidence"])
    return result["profile"]


def _profile_step() -> None:
    profile = render_profile_page(extractor=_extract_with_evidence, choose_source=True)
    if profile is not None:
        _sync_profile_draft()
        if st.session_state.pop(PROFILE_JUST_SAVED_SESSION_KEY, False):
            st.session_state[APP_PREFIX + "page"] = "2. Xác nhận"
            st.rerun()
        st.button("Tiếp tục: Kiểm tra thông tin →", type="primary", key="p09_profile_next",
                  on_click=lambda: st.session_state.update({APP_PREFIX + "page": "2. Xác nhận"}))


def _review_step() -> None:
    draft = _sync_profile_draft()
    if draft is None:
        _clear_after_profile()
        st.warning("Hãy nhập thông tin ở Bước 1 trước.")
        return
    # Do not feed Person 4's edited widget values back as new upstream drafts.
    # Doing so would re-seed the review page and invalidate confirmations.
    bundle = render_review_page(draft, INITIAL_ASSUMPTIONS)
    st.session_state[APP_PREFIX + "review_bundle"] = bundle
    if bundle is None:
        _clear_after_review()
        return
    st.button("Xem kế hoạch của tôi →", type="primary", key="p09_review_next",
              on_click=lambda: st.session_state.update({APP_PREFIX + "page": "3. Mô phỏng"}))


def _scenario_step() -> None:
    reviewed = st.session_state.get(APP_PREFIX + "review_bundle")
    if not isinstance(reviewed, dict):
        _clear_after_review()
        st.warning("Hãy kiểm tra và xác nhận thông tin ở Bước 2 trước.")
        return
    profile = reviewed["profile"]
    assumptions = reviewed["assumptions"]
    validation = reviewed["validation_result"]
    scenario_output = render_scenario_page(
        profile,
        assumptions,
        validation_status=validation["status"],
        profile_confirmed=reviewed.get("profile_confirmed") is True,
    )
    if scenario_output is None:
        st.session_state[APP_PREFIX + "scenario_bundle"] = None
        _clear_after_scenario()
        return
    try:
        base = scenario_output["scenarios"]["base"]
        final_assumptions = dict(base["assumptions"])
        calculation_result = base["calculation_result"]
    except (KeyError, TypeError, ValueError):
        st.session_state[APP_PREFIX + "scenario_bundle"] = None
        _clear_after_scenario()
        st.error("Kế hoạch chưa được tạo đầy đủ. Vui lòng thử lại.")
        return
    final_validation = validate_profile(profile, final_assumptions)
    if (final_validation.get("status") not in {"VALID", "WARNING"}
            or final_validation.get("can_simulate") is not True):
        st.session_state[APP_PREFIX + "scenario_bundle"] = None
        _clear_after_scenario()
        st.error("Một số thông tin chưa phù hợp để lập kế hoạch. Hãy quay lại kiểm tra.")
        for issue in final_validation.get("errors", []):
            st.write("- " + str(issue.get("message", issue)))
        return
    scenario_bundle = {
        "profile": profile,
        "assumptions": final_assumptions,
        "calculation_result": calculation_result,
        "scenario_result": scenario_output,
        "validation_result": final_validation,
        "profile_confirmed": True,
        "assumptions_confirmed": scenario_output.get("assumptions_confirmed") is True,
    }
    old = st.session_state.get(APP_PREFIX + "scenario_bundle")
    if not isinstance(old, dict) or _fingerprint(old) != _fingerprint(scenario_bundle):
        _clear_after_scenario()
    st.session_state[APP_PREFIX + "scenario_bundle"] = scenario_bundle
    with st.expander("Xem cách tính và các chỉ số chi tiết · Không bắt buộc"):
        render_cashflow_page(profile, final_assumptions)
    st.button("Tiếp tục: Tạo báo cáo →", type="primary", key="p09_scenario_next",
              disabled=not scenario_bundle["assumptions_confirmed"],
              on_click=lambda: st.session_state.update({APP_PREFIX + "page": "4. Báo cáo"}))


def _report_step() -> None:
    bundle = st.session_state.get(APP_PREFIX + "scenario_bundle")
    if not isinstance(bundle, dict):
        _clear_after_scenario()
        st.warning("Hãy hoàn thành Bước 3 để tạo kết quả mô phỏng trước khi lập báo cáo.")
    else:
        report = render_report_page(
            bundle["profile"],
            bundle["calculation_result"],
            bundle["scenario_result"],
            bundle["validation_result"],
            profile_confirmed=bundle.get("profile_confirmed") is True,
            assumptions_confirmed=bundle.get("assumptions_confirmed") is True,
        )
        st.session_state[APP_PREFIX + "report_bundle"] = report
    if os.environ.get("PROJECT09_SHOW_TECHNICAL") == "1":
        with st.expander("Vai trò LLM và minh chứng hệ thống", expanded=False):
            render_llm_showcase()
            st.caption("Phần này trình bày kết quả đánh giá hệ thống và không thuộc báo cáo tài chính cá nhân.")
            render_evaluation_panel()


def main() -> None:
    st.set_page_config(page_title="Project 09 | Kế hoạch tài chính", page_icon="◈", layout="wide",
                       initial_sidebar_state="collapsed")
    load_theme()
    st.session_state.setdefault(APP_PREFIX + "page", "Tổng quan")
    # Keep edit buffers and explicit confirmations when their page is hidden.
    # Streamlit otherwise removes widget keys at the end of a navigation run.
    ephemeral_buttons = {"person3_reset", "person4_reset", "person4_load_sample", "person4_extract",
                         "person5_explain", "person5_create_pdf", "person5_download"}
    for key in list(st.session_state):
        if key not in ephemeral_buttons and str(key).startswith(("person3_", "person4_", "person5_", "profile_input_", "natural_input_")):
            st.session_state[key] = st.session_state[key]
    _top_navigation()
    page = st.session_state[APP_PREFIX + "page"]
    if page == "Tổng quan":
        _overview()
    else:
        _page_banner(page)
        with st.container(key="p09_inner_page"):
            _page_actions(page)
            if page == "1. Hồ sơ":
                _profile_step()
            elif page == "2. Xác nhận":
                _review_step()
            elif page == "3. Mô phỏng":
                _scenario_step()
            else:
                _report_step()


if __name__ == "__main__":
    main()
