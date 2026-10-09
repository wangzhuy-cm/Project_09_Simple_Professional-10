"""Simple, professional presentation for Person 3's scenario engine.

The calculation contracts stay unchanged. This module only translates their
outputs into plain-language choices for students and young adults. Technical
assumptions remain available in collapsed sections for audit and teaching.
"""
from __future__ import annotations

import hashlib
from html import escape
import json
from pathlib import Path
import sys

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.charts import (
    build_comparison_table,
    create_balance_chart,
    create_cashflow_chart,
    create_final_value_chart,
    create_goal_progress_chart,
    create_scenario_detail_chart,
)
from src.market_reference import MarketReferenceError, load_market_reference
from src.scenarios import (ScenarioInputError, build_scenarios, load_scenario_defaults,
                           prepare_inputs, run_what_if)
from src.stress_test import run_stress_test
from ui.theme import money


SCENARIO_NAMES_VI = {
    "conservative": ("Thận trọng", "Ưu tiên an toàn khi điều kiện kém thuận lợi."),
    "base": ("Cơ sở", "Phương án chính dựa trên thông tin hiện tại."),
    "optimistic": ("Tích cực", "Kết quả tốt hơn khi dòng tiền thuận lợi."),
}

SCENARIO_GUIDANCE = {
    "conservative": (
        "Khi nào nên xem", "Dùng để kiểm tra biên an toàn nếu thu nhập hoặc khả năng dành tiền thấp hơn dự kiến.",
        "Cách đọc", "Nếu phương án này vẫn đạt mục tiêu, kế hoạch của bạn có khoảng đệm tốt hơn trước biến động.",
    ),
    "base": (
        "Khi nào nên xem", "Đây là phương án chính, bám sát thông tin bạn vừa xác nhận và giả định hiện tại.",
        "Cách đọc", "Dùng phương án này để quyết định số tiền cần dành mỗi tháng và theo dõi tiến độ thực tế.",
    ),
    "optimistic": (
        "Khi nào nên xem", "Dùng để hình dung kết quả khi dòng tiền thuận lợi hơn; đây không phải cam kết lợi nhuận.",
        "Cách đọc", "Hãy coi phần vượt mục tiêu là dư địa tiềm năng, không phải cơ sở duy nhất để ra quyết định.",
    ),
}

WARNING_TEXT = {
    "income_growth_not_applied_in_mvp": "Tăng trưởng thu nhập chưa được tự động đưa vào kế hoạch.",
    "negative_monthly_cash_flow": "Chi tiêu đang cao hơn thu nhập. Hãy xử lý phần thiếu hụt trước.",
    "monthly_contribution_exceeds_current_surplus": "Số tiền dự kiến dành mỗi tháng cao hơn dòng tiền còn lại.",
    "required_monthly_contribution_exceeds_current_surplus": "Số tiền cần dành mỗi tháng đang vượt khả năng hiện tại.",
    "goal_not_reached_within_projection_limit": "Kế hoạch hiện tại chưa đạt mục tiêu trong khoảng thời gian hỗ trợ.",
    "emergency_fund_reserved_exceeds_current_savings": "Tiền tiết kiệm hiện có chưa đủ phần quỹ dự phòng muốn giữ lại.",
    "goal_already_funded_from_available_savings": "Tiền có thể sử dụng hiện đã đủ cho mục tiêu.",
    "scenario_return_rate_clipped_to_demo_limit": "Hệ thống đã giới hạn lợi suất để phù hợp mức rủi ro đã chọn.",
    "unfunded_cashflow_deficit_not_deducted_from_goal_or_emergency_fund": "Mô hình chưa dùng quỹ dự phòng để bù thiếu hụt sinh hoạt.",
    "stress_window_truncated_at_goal_horizon_for_final_balance": "Cú sốc kéo dài quá thời hạn mục tiêu nên chỉ phần trong thời hạn được tính.",
}

METRIC_LABELS = {
    "monthly_contribution": "Dành mỗi tháng (VND)",
    "fv_total": "Giá trị dự kiến cuối kỳ (VND)",
    "goal_gap": "Số tiền còn thiếu (+) / vượt (−) (VND)",
    "goal_reached_by_horizon": "Đạt mục tiêu đúng hạn",
    "estimated_month_to_goal": "Tháng dự kiến đạt mục tiêu",
    "required_monthly_contribution": "Số tiền cần dành mỗi tháng (VND)",
    "contribution_affordability_gap": "Phần đóng góp vượt dòng tiền (VND/tháng)",
    "required_contribution_gap": "Phần cần dành vượt dòng tiền (VND/tháng)",
    "emergency_fund_available": "Quỹ dự phòng được giữ lại (VND)",
    "total_contributions": "Tổng tiền tự tích lũy (VND)",
    "investment_gain": "Phần tăng/giảm theo giả định (VND)",
}


def _reset_state() -> None:
    import streamlit as st
    for key in list(st.session_state):
        if str(key).startswith("person3_") and key != "person3_source_fingerprint":
            del st.session_state[key]


def _month_text(value) -> str:
    return "Chưa xác định" if value is None else f"Tháng {int(value)}"


def _scenario_cards(result: dict) -> str:
    cards = []
    for key in ("conservative", "base", "optimistic"):
        item = result[key]
        metrics = item["calculation_result"]
        name, note = SCENARIO_NAMES_VI[key]
        reached = metrics["goal_reached_by_horizon"]
        outcome = "Đạt mục tiêu" if reached else "Còn thiếu " + money(max(metrics["goal_gap"], 0))
        tone = "is-good" if reached else "is-caution"
        cards.append(
            '<article class="p09-scenario-card is-' + key + '">'
            f'<span>{escape(name.upper())}</span><h3>{escape(money(metrics["fv_total"]))}</h3>'
            f'<strong class="{tone}">{escape(outcome)}</strong>'
            f'<p>{escape(note)}</p><small>{escape(_month_text(metrics["estimated_month_to_goal"]))}</small>'
            '</article>'
        )
    return '<div class="p09-scenario-grid">' + ''.join(cards) + '</div>'


def _technical_result(result: dict, key: str) -> None:
    """Keep the complete audit view available without dominating the journey."""
    import streamlit as st

    table = build_comparison_table(result)
    formatted = table.copy()
    for metric in table.index:
        for column in table.columns:
            value = table.at[metric, column]
            if value is None:
                text = "Chưa xác định"
            elif metric == "goal_reached_by_horizon":
                text = "Có" if value else "Chưa"
            elif metric == "estimated_month_to_goal":
                text = str(int(value))
            else:
                text = f"{value:,.0f}".replace(",", ".")
            formatted.at[metric, column] = text
    st.dataframe(formatted.rename(index=METRIC_LABELS, columns={
        "Conservative": "Thận trọng", "Base": "Cơ sở", "Optimistic": "Tích cực",
        "Trước stress": "Trước cú sốc", "Sau stress": "Sau cú sốc",
    }), width="stretch")
    st.plotly_chart(create_final_value_chart(result), width="stretch", key=f"{key}_bar")


def _warnings(result: dict) -> list[str]:
    warnings = []
    for item in result.values():
        if isinstance(item, dict) and isinstance(item.get("warnings"), list):
            warnings.extend(item["warnings"])
    return list(dict.fromkeys(warnings))


def _render_scenario_focus(scenarios: dict) -> None:
    """Turn the three scenarios into a clear, selectable explanation."""
    import streamlit as st

    options = ("conservative", "base", "optimistic")
    selected = st.radio(
        "Chọn một phương án để xem chi tiết",
        options,
        index=1,
        format_func=lambda key: SCENARIO_NAMES_VI[key][0],
        horizontal=True,
        key="person3_scenario_focus",
    )
    item = scenarios[selected]
    metrics = item["calculation_result"]
    name, note = SCENARIO_NAMES_VI[selected]
    status = "Đạt đúng hạn" if metrics["goal_reached_by_horizon"] else "Chưa đạt đúng hạn"
    st.markdown(
        '<section class="p09-scenario-explainer">'
        f'<div><span>ĐANG XEM · {escape(status.upper())}</span><h3>{escape(name)}</h3></div>'
        f'<p>{escape(note)} Dự kiến có {escape(money(metrics["fv_total"]))}, '
        f'dành {escape(money(metrics["monthly_contribution"]))}/tháng.</p>'
        '</section>',
        unsafe_allow_html=True,
    )
    left, right = st.columns(2, gap="large")
    with left:
        st.plotly_chart(create_goal_progress_chart(item), width="stretch", key="dashboard_goal")
    with right:
        st.plotly_chart(create_cashflow_chart(item), width="stretch", key="dashboard_cashflow")
    st.plotly_chart(
        create_scenario_detail_chart(item), width="stretch",
        key=f"scenario_focus_{selected}",
    )
    st.caption("Ba biểu đồ đang cùng hiển thị phương án " + name.lower() +
               ". Báo cáo vẫn lấy phương án cơ sở làm kế hoạch chính và kèm cả ba phương án để so sánh.")
    if metrics.get("contribution_affordability_gap", 0) > 0:
        st.warning("Khoản dành cho mục tiêu vượt dòng tiền còn lại. Phân bổ trên là kế hoạch cần nguồn bù, không phải dòng tiền đã bảo đảm.")


def render_scenario_page(profile: dict, base_assumptions: dict, *,
                         validation_status: str | None = None,
                         profile_confirmed: bool = False, demo_mode: bool = False) -> dict | None:
    """Render a plain-language plan while preserving Person 3's public output."""
    import streamlit as st

    with st.container(key="p09_accessible_scenario_title"):
        st.header("Kế hoạch của bạn")
    st.markdown('<div class="p09-form-intro"><span>03 / KẾ HOẠCH CỦA BẠN</span>'
                '<h2>Bạn đang tiến gần mục tiêu đến đâu?</h2>'
                '<p>Xem kết quả chính trước, sau đó thử thay đổi kế hoạch nếu cần.</p></div>',
                unsafe_allow_html=True)
    if not demo_mode and (validation_status not in {"VALID", "WARNING"} or not profile_confirmed):
        st.info("Hãy kiểm tra và xác nhận thông tin trước khi xem kế hoạch.")
        return None

    try:
        p, a = prepare_inputs(profile, base_assumptions)
        fingerprint = hashlib.sha256(json.dumps([p, a], sort_keys=True).encode()).hexdigest()
        if st.session_state.get("person3_source_fingerprint") != fingerprint:
            _reset_state()
            st.session_state["person3_source_fingerprint"] = fingerprint

        if demo_mode:
            st.warning("Chế độ demo độc lập sử dụng hồ sơ giả lập.")
            if not st.checkbox("Tôi đã kiểm tra hồ sơ mẫu", key="person3_profile_confirmed"):
                return None

        cfg = load_scenario_defaults()
        cap = cfg["limits"]["max_annual_return_rate_by_risk"][p["risk_tolerance"]]
        with st.expander("Giả định nâng cao và nguồn tham chiếu · Không bắt buộc", expanded=False):
            st.caption("Bạn có thể giữ nguyên các giá trị mặc định. Đây là giả định giáo dục, không phải dự báo lợi nhuận.")
            left, right = st.columns(2, gap="large")
            with left:
                rate = st.number_input(
                    "Lợi suất giả định (%/năm)",
                    min_value=float(cfg["limits"]["min_annual_return_rate"] * 100),
                    max_value=cap * 100,
                    value=float(a["annual_return_rate"] * 100), step=0.5,
                    key="person3_return",
                ) / 100
            with right:
                inflation = st.number_input(
                    "Lạm phát giả định (%/năm)",
                    min_value=float(cfg["limits"]["min_annual_inflation_rate"] * 100),
                    max_value=float(cfg["limits"]["max_annual_inflation_rate"] * 100),
                    value=float(a.get("annual_inflation_rate", 0) * 100), step=0.5,
                    key="person3_inflation",
                ) / 100
            try:
                reference = load_market_reference()
                st.caption("Bản tham chiếu đóng gói ngày " + reference["retrieved_on"] + ". Không tự cập nhật trực tuyến.")
                st.write(reference["usage_note"])
                for ref_col, indicator in zip(st.columns(2), reference["indicators"].values()):
                    with ref_col:
                        st.markdown("**" + indicator["label"] + "**")
                        st.write(indicator["display_value"] + " · " + indicator["source"])
                        st.caption(indicator["reference_period"])
                        st.link_button("Mở nguồn tham khảo", indicator["source_url"])
                        if indicator.get("verification_url"):
                            st.link_button("Nguồn để đối chiếu", indicator["verification_url"])
            except MarketReferenceError:
                st.caption("Không đọc được dữ liệu tham chiếu; các giả định hiện tại vẫn được giữ nguyên.")
            with st.expander("Cách hệ thống tạo ba phương án"):
                rows = []
                for item in cfg["scenarios"].values():
                    rows.append({
                        "Phương án": item["label"],
                        "Thu nhập": f'{(item["income_multiplier"] - 1) * 100:+.0f}%',
                        "Chi tiêu linh hoạt": f'{(item["discretionary_expense_multiplier"] - 1) * 100:+.0f}%',
                        "Mức dành mỗi tháng": (f'{min(item["contribution_multiplier"], 1) * 100:.0f}% dòng tiền còn lại'
                            if a.get("monthly_contribution") is None else f'{(item["contribution_multiplier"] - 1) * 100:+.0f}% mức cố định'),
                        "Điều chỉnh lợi suất": f'{item["annual_return_rate_offset"] * 100:+.1f} điểm %',
                    })
                st.dataframe(rows, width="stretch", hide_index=True)
            st.button("Khôi phục thiết lập ban đầu", key="person3_reset", on_click=_reset_state)

        a.update(annual_return_rate=rate, annual_inflation_rate=inflation)
        scenarios = build_scenarios(p, a)
        output = {"scenarios": scenarios, "what_if": None, "stress_test": None, "is_final_plan": False}
        base = scenarios["base"]["calculation_result"]
        reached = base["goal_reached_by_horizon"]
        month = base["estimated_month_to_goal"]
        if reached:
            headline = "Bạn có khả năng đạt mục tiêu"
            detail = (f"Với kế hoạch hiện tại, bạn có thể đạt mục tiêu vào tháng {int(month)}."
                      if month is not None else "Kế hoạch hiện tại đủ đạt mục tiêu trong thời hạn.")
            tone = "is-positive"
        else:
            headline = "Kế hoạch hiện tại chưa đủ để đạt mục tiêu"
            detail = "Bạn có thể điều chỉnh số tiền dành mỗi tháng hoặc kéo dài thời hạn."
            tone = "is-warning"
        st.markdown(
            f'<section class="p09-plan-outcome {tone}"><span>KẾT LUẬN CHÍNH</span>'
            f'<h2>{escape(headline)}</h2><p>{escape(detail)}</p></section>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="p09-plan-metrics">'
            f'<div><span>Mục tiêu cần đạt</span><strong>{escape(money(base["adjusted_goal_amount"]))}</strong></div>'
            f'<div><span>Dự kiến có</span><strong>{escape(money(base["fv_total"]))}</strong></div>'
            f'<div><span>Đang dành mỗi tháng · cơ sở</span><strong>{escape(money(base["monthly_contribution"]))}</strong></div>'
            '</div>', unsafe_allow_html=True,
        )
        if base["required_contribution_gap"] > 0:
            st.warning("Để đạt đúng hạn, bạn còn cần thêm " + money(base["required_contribution_gap"]) + " mỗi tháng so với dòng tiền hiện tại.")

        _render_scenario_focus(scenarios)

        with st.expander("Xem so sánh cả ba phương án", expanded=False):
            st.caption("Mở phần này khi bạn muốn đối chiếu kết quả cuối kỳ và tiến trình của cả ba phương án.")
            st.plotly_chart(create_final_value_chart(scenarios), width="stretch", key="dashboard_scenario_bars")
            st.plotly_chart(create_balance_chart(scenarios), width="stretch", key="scenarios_line")
            for warning in _warnings(scenarios):
                message = WARNING_TEXT.get(warning)
                if message and warning != "income_growth_not_applied_in_mvp":
                    st.warning(message)

        with st.expander("Xem bảng số liệu chi tiết", expanded=False):
            table = build_comparison_table(scenarios)
            formatted = table.copy()
            for metric in table.index:
                for column in table.columns:
                    value = table.at[metric, column]
                    if value is None:
                        text = "Chưa xác định"
                    elif metric == "goal_reached_by_horizon":
                        text = "Có" if value else "Chưa"
                    elif metric == "estimated_month_to_goal":
                        text = str(int(value))
                    else:
                        text = f"{value:,.0f}".replace(",", ".")
                    formatted.at[metric, column] = text
            st.dataframe(formatted.rename(index=METRIC_LABELS, columns={
                "Conservative": "Thận trọng", "Base": "Cơ sở", "Optimistic": "Tích cực",
            }), width="stretch")

        with st.expander("Thử thay đổi kế hoạch", expanded=False):
            st.markdown("### Nếu bạn thay đổi kế hoạch thì sao?")
            st.caption("Thử các con số mới. Thông tin ban đầu của bạn không bị thay đổi.")
            left, right = st.columns(2, gap="large")
            with left:
                primary_income = st.number_input(
                    "Thu nhập chính mỗi tháng", min_value=0.0,
                    value=float(p["monthly_primary_income"]), step=100000.0,
                    key="person3_wi_monthly_primary_income",
                )
                essential = st.number_input(
                    "Chi phí thiết yếu mỗi tháng", min_value=0.0,
                    value=float(p["monthly_essential_expense"]), step=100000.0,
                    key="person3_wi_monthly_essential_expense",
                )
            with right:
                horizon = st.number_input(
                    "Thời hạn mục tiêu (tháng)", min_value=1, max_value=120,
                    value=p["goal_horizon_months"], key="person3_wi_horizon",
                )
                auto = st.checkbox(
                    "Tự động dùng dòng tiền còn lại",
                    value=a.get("monthly_contribution") is None,
                    key="person3_wi_auto",
                )
                contribution = None
                if not auto:
                    contribution = st.number_input(
                        "Số tiền muốn dành mỗi tháng", min_value=0.0,
                        value=float(base["monthly_contribution"]), step=100000.0,
                        key="person3_wi_contribution",
                    )
            updates = {
                "monthly_primary_income": primary_income,
                "monthly_essential_expense": essential,
                "goal_horizon_months": horizon,
            }
            what_if = run_what_if(p, a, updates, {"monthly_contribution": contribution})
            output["what_if"] = what_if
            changed = what_if["modified"]["calculation_result"]
            result_text = "Đạt mục tiêu" if changed["goal_reached_by_horizon"] else "Chưa đạt mục tiêu"
            st.markdown(
                '<div class="p09-whatif-result">'
                f'<span>KẾT QUẢ SAU THAY ĐỔI</span><h3>{escape(result_text)}</h3>'
                f'<p>Dự kiến có <strong>{escape(money(changed["fv_total"]))}</strong> sau '
                f'{int(changed["goal_horizon_months"])} tháng · {_month_text(changed["estimated_month_to_goal"])}.</p>'
                '</div>', unsafe_allow_html=True,
            )
            with st.expander("Xem so sánh chi tiết", expanded=False):
                _technical_result(what_if, "what_if")

        with st.expander("Nếu thu nhập giảm?", expanded=False):
            st.markdown("### Nếu thu nhập tạm thời giảm thì sao?")
            st.caption("Thử một tình huống khó để biết kế hoạch có cần khoảng đệm hay không.")
            left, right = st.columns(2)
            with left:
                reduction_percent = st.select_slider(
                    "Mức giảm thu nhập", options=[10, 20, 30], value=20,
                    format_func=lambda value: f"Giảm {value}%", key="person3_stress_reduction",
                )
            with right:
                duration = st.selectbox(
                    "Kéo dài trong", options=[3, 6], index=0,
                    format_func=lambda value: f"{value} tháng", key="person3_stress_duration",
                )
            stress = run_stress_test(p, a, {
                "income_reduction_rate": reduction_percent / 100,
                "duration_months": duration,
                "start_month": 1,
            })
            output["stress_test"] = stress
            cmp = stress["comparison"]
            deficit = cmp.get("unfunded_cashflow_deficit", 0)
            delayed = cmp["goal_delay_months"]
            if delayed is None:
                delay_text = "chưa xác định được thời điểm đạt mục tiêu"
            elif delayed == 0:
                delay_text = "thời điểm đạt mục tiêu không đổi"
            else:
                delay_text = f"mục tiêu có thể chậm khoảng {int(delayed)} tháng"
            st.markdown(
                '<div class="p09-stress-result"><span>TÁC ĐỘNG ƯỚC TÍNH</span>'
                f'<h3>Giá trị cuối kỳ giảm {escape(money(cmp["fv_total_reduction"]))}</h3>'
                f'<p>Nếu thu nhập giảm {reduction_percent}% trong {duration} tháng, {escape(delay_text)}.</p></div>',
                unsafe_allow_html=True,
            )
            before_month = stress["baseline"]["calculation_result"]["estimated_month_to_goal"]
            after_month = stress["stressed"]["calculation_result"]["estimated_month_to_goal"]
            st.caption(f"Tháng đạt mục tiêu: {_month_text(before_month)} → {_month_text(after_month)}. "
                       f"Hạn gốc: tháng {p['goal_horizon_months']}; kéo dài so với hạn gốc: "
                       + ("chưa xác định." if cmp.get("extension_months_from_original_horizon") is None
                          else f"{cmp['extension_months_from_original_horizon']} tháng."))
            if deficit > 0:
                st.warning("Thiếu " + money(deficit) + " để trang trải sinh hoạt trong cú sốc. "
                           "Khoản này CHƯA trừ khỏi tiền mục tiêu hay quỹ dự phòng; kết quả chỉ đúng nếu có nguồn khác bù thiếu hụt.")
            if cmp.get("recovery_required_contribution_gap", 0) and cmp["recovery_required_contribution_gap"] > 0:
                st.warning("Mức bù sau cú sốc đang vượt dòng tiền. Hãy cân nhắc kéo dài thời hạn hoặc giảm mục tiêu.")
            with st.expander("Xem số liệu kiểm tra sức chịu đựng", expanded=False):
                _technical_result(stress, "stress")
        confirmation_signature = hashlib.sha256(json.dumps([p, a, output["what_if"]["changes"],
            reduction_percent, duration], sort_keys=True).encode()).hexdigest()
        if st.session_state.get("person3_confirmation_signature") != confirmation_signature:
            st.session_state["person3_assumptions_confirmed"] = False
            st.session_state["person3_confirmation_signature"] = confirmation_signature
        st.markdown('<div class="p09-confirmation"><b>GIẢ ĐỊNH DÙNG TRONG BÁO CÁO</b>'
                    f'<p>Lợi suất {rate * 100:.2f}%/năm · Lạm phát {inflation * 100:.2f}%/năm · '
                    f'Thời hạn {p["goal_horizon_months"]} tháng. Góp tiền cuối tháng; chưa tính thuế, phí và tăng thu nhập. '
                    'Nhu cầu rút tiền chỉ ghi nhận, chưa mô phỏng. Mọi thay đổi giả định hoặc phép thử cần xác nhận lại.</p></div>', unsafe_allow_html=True)
        confirmed = st.checkbox("Tôi đã xem và xác nhận các giả định, phép thử của báo cáo",
                                key="person3_assumptions_confirmed")
        output["assumptions_confirmed"] = confirmed
        output["assumptions_fingerprint"] = confirmation_signature
        if demo_mode and not confirmed:
            return None
        return output
    except (ScenarioInputError, ValueError, TypeError, KeyError) as exc:
        st.error(f"Chưa thể tạo kế hoạch: {exc}")
        return None


def _standalone_demo() -> None:
    import streamlit as st

    st.set_page_config(page_title="Project 09 - Kế hoạch tài chính", layout="wide")
    data_path = Path(__file__).resolve().parents[1] / "data" / "test_cases.json"
    if not data_path.exists():
        st.error("Không tìm thấy dữ liệu cho tình huống minh họa.")
        return
    cases = json.loads(data_path.read_text(encoding="utf-8"))["cases"]
    allowed = [case for case in cases if case["expected_profile"]["user_id"] in {"P001", "P006", "P019"}]
    profiles = {case["expected_profile"]["user_id"]: case["expected_profile"] for case in allowed}
    selected = st.selectbox("Hồ sơ giả lập", list(profiles), index=list(profiles).index("P019"))
    render_scenario_page(profiles[selected], {"annual_return_rate": 0.0}, demo_mode=True)


if __name__ == "__main__":
    _standalone_demo()


__all__ = ["render_scenario_page"]
