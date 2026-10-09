"""Person 3 contract, financial regression, charts and Streamlit interaction tests.

Run from the project root: python -m pytest -q tests/test_scenarios.py
Requires the unchanged schemas/calculations dependencies from Persons 1 and 2.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.calculations import calculate_financial_metrics
from src.scenarios import (ScenarioInputError, build_scenarios, load_scenario_defaults,
                           run_what_if)
from src.stress_test import run_stress_test
from src.charts import build_comparison_table, create_balance_chart, create_final_value_chart


@pytest.fixture
def profile():
    # Person 1 P019: baseline 130m, shocked 118m at month 24 under zero return.
    return {
        "user_id": "P019", "monthly_primary_income": 18_000_000,
        "monthly_other_income": 2_000_000, "monthly_essential_expense": 11_000_000,
        "monthly_discretionary_expense": 3_000_000, "monthly_debt_payment": 1_000_000,
        "current_savings": 30_000_000, "emergency_fund_reserved": 20_000_000,
        "goal_name": "Học cao học", "goal_amount": 120_000_000,
        "goal_horizon_months": 24, "risk_tolerance": "medium",
        "liquidity_need": "medium", "expected_income_growth": 0.06,
        "notes": "Dùng cho stress test thu nhập giảm 20% trong 3 tháng.",
    }


def test_three_scenarios_and_baseline_exact_engine_match(profile):
    assumptions = {"annual_return_rate": 0.02}
    result = build_scenarios(profile, assumptions)
    assert result["base"]["calculation_result"] == calculate_financial_metrics(profile, assumptions)
    assert result["conservative"]["calculation_result"]["fv_total"] < result["base"]["calculation_result"]["fv_total"]
    assert result["base"]["calculation_result"]["fv_total"] < result["optimistic"]["calculation_result"]["fv_total"]
    for name in ("conservative", "base", "optimistic"):
        item = result[name]
        assert len(item["monthly_projection"]) == 25
        assert item["monthly_projection"][-1]["balance"] == pytest.approx(item["calculation_result"]["fv_total"])
        assert item["emergency_fund_available"] == 20_000_000
        assert item["profile_used"]["monthly_debt_payment"] == profile["monthly_debt_payment"]
        assert item["profile_used"]["monthly_essential_expense"] == profile["monthly_essential_expense"]


def test_all_public_operations_do_not_mutate_inputs(profile):
    assumptions = {"annual_return_rate": 0.0, "monthly_contribution": 4_000_000}
    config = {"income_reduction_rate": 0.2, "start_month": 2, "duration_months": 3}
    changes = {"monthly_primary_income": 19_000_000}
    snapshot = deepcopy((profile, assumptions, config, changes))
    build_scenarios(profile, assumptions)
    run_what_if(profile, assumptions, changes)
    run_stress_test(profile, assumptions, config)
    assert (profile, assumptions, config, changes) == snapshot


def test_scenario_result_is_serializable_and_independent(profile):
    result = build_scenarios(profile, {"annual_return_rate": 0.0})
    json.dumps(result, allow_nan=False)
    result["optimistic"]["profile_used"]["current_savings"] = -1
    assert result["base"]["profile_used"]["current_savings"] == 30_000_000
    assert profile["current_savings"] == 30_000_000


def test_explicit_contribution_keeps_affordability_warning(profile):
    result = build_scenarios(profile, {"annual_return_rate": 0.0, "monthly_contribution": 9_000_000})
    base = result["base"]["calculation_result"]
    assert base["contribution_affordability_gap"] == 4_000_000
    assert "monthly_contribution_exceeds_current_surplus" in base["calculation_warnings"]


def test_rate_clipping_is_disclosed(profile):
    profile["risk_tolerance"] = "low"
    result = build_scenarios(profile, {"annual_return_rate": 0.06})
    assert result["optimistic"]["requested_annual_return_rate"] == pytest.approx(0.07)
    assert result["optimistic"]["assumptions"]["annual_return_rate"] == 0.06
    assert "scenario_return_rate_clipped_to_demo_limit" in result["optimistic"]["warnings"]


@pytest.mark.parametrize("field,value", [
    ("goal_horizon_months", None), ("goal_horizon_months", 0),
    ("goal_horizon_months", 121), ("goal_horizon_months", True),
    ("monthly_other_income", None), ("monthly_primary_income", -1),
    ("goal_amount", 0), ("goal_amount", "120000000"),
    ("risk_tolerance", None), ("liquidity_need", None),
])
def test_bad_profiles_are_controlled(profile, field, value):
    profile[field] = value
    with pytest.raises(ScenarioInputError):
        build_scenarios(profile, {"annual_return_rate": 0.0})


@pytest.mark.parametrize("assumptions", [
    {}, {"annual_return_rate": None}, {"annual_return_rate": float("nan")},
    {"annual_return_rate": 0.8}, {"annual_return_rate": -1},
    {"annual_return_rate": 0, "expected_income_growth": 0.1},
    {"annual_return_rate": 0, "max_projection_months": 5},
    {"annual_return_rate": 0, "monthly_contribution": -1},
    {"annual_return_rate": 0, "annual_inflation_rate": None},
])
def test_bad_assumptions_are_controlled(profile, assumptions):
    with pytest.raises(ScenarioInputError):
        build_scenarios(profile, assumptions)


@pytest.mark.parametrize("updates,expected_contribution", [
    ({"monthly_primary_income": 19_000_000}, 6_000_000),
    ({"monthly_other_income": 3_000_000}, 6_000_000),
    ({"monthly_discretionary_expense": 2_000_000}, 6_000_000),
    ({"monthly_essential_expense": 10_000_000}, 6_000_000),
    ({"monthly_debt_payment": 0}, 6_000_000),
])
def test_what_if_recomputes_automatic_contribution(profile, updates, expected_contribution):
    result = run_what_if(profile, {"annual_return_rate": 0}, updates)
    assert result["modified"]["calculation_result"]["monthly_contribution"] == expected_contribution
    assert result["comparison"]["fv_total_change"] == pytest.approx(24_000_000)


def test_what_if_explicit_pmt_is_not_silently_recomputed(profile):
    result = run_what_if(profile, {"annual_return_rate": 0, "monthly_contribution": 5_000_000},
                         {"monthly_primary_income": 16_000_000})
    m = result["modified"]["calculation_result"]
    assert m["monthly_contribution"] == 5_000_000
    assert m["contribution_affordability_gap"] == 2_000_000
    reset = run_what_if(profile, {"annual_return_rate": 0, "monthly_contribution": 2_000_000},
                        assumption_updates={"monthly_contribution": None})
    assert reset["modified"]["calculation_result"]["monthly_contribution"] == 5_000_000


def test_what_if_horizon_goal_and_rate_match_engine(profile):
    changed = {"goal_horizon_months": 36, "goal_amount": 150_000_000}
    assumptions = {"annual_return_rate": 0.04, "annual_inflation_rate": 0.02, "monthly_contribution": 6_000_000}
    result = run_what_if(profile, {"annual_return_rate": 0}, changed, assumptions)
    assert result["modified"]["calculation_result"] == calculate_financial_metrics({**profile, **changed}, assumptions)
    assert result["comparison"]["horizons_differ"] is True


def test_what_if_rejects_unknown_fields(profile):
    with pytest.raises(ScenarioInputError):
        run_what_if(profile, {"annual_return_rate": 0}, {"income": 10})


def test_p019_required_stress_regression_and_recovery(profile):
    result = run_stress_test(profile, {"annual_return_rate": 0.0}, {})
    before = result["baseline"]["calculation_result"]
    after = result["stressed"]["calculation_result"]
    cmp = result["comparison"]
    assert before["fv_total"] == 130_000_000
    assert after["fv_total"] == 118_000_000
    assert before["goal_gap"] == -10_000_000
    assert after["goal_gap"] == 2_000_000
    assert before["estimated_month_to_goal"] == 22
    assert after["estimated_month_to_goal"] == 25
    assert cmp["goal_delay_months"] == 3
    assert cmp["extension_months_from_original_horizon"] == 1
    assert cmp["recovery_required_monthly_contribution"] == pytest.approx(107_000_000 / 21)
    assert cmp["additional_monthly_contribution_after_stress"] == pytest.approx(2_000_000 / 21)
    assert cmp["recovery_required_contribution_gap"] == pytest.approx(2_000_000 / 21)
    assert after["required_monthly_contribution"] is None
    json.dumps(result, allow_nan=False)


def test_shock_affects_exactly_three_months_and_both_incomes(profile):
    result = run_stress_test(profile, {"annual_return_rate": 0.0}, {"start_month": 4})
    rows = result["stressed"]["monthly_projection"]
    assert [r["month"] for r in rows if r["stress_active"]] == [4, 5, 6]
    assert rows[3]["total_monthly_income"] == 20_000_000
    assert rows[4]["total_monthly_income"] == 16_000_000
    assert rows[6]["monthly_contribution"] == 1_000_000
    assert rows[7]["total_monthly_income"] == 20_000_000
    assert rows[7]["monthly_contribution"] == 5_000_000


def test_nonzero_interest_stress_matches_independent_monthly_oracle(profile):
    a = {"annual_return_rate": 0.06, "annual_inflation_rate": 0.03}
    result = run_stress_test(profile, a, {"start_month": 5})
    rate = (1 + 0.06) ** (1 / 12) - 1
    inf = (1 + 0.03) ** (1 / 12) - 1
    balance = 10_000_000.0
    first = None
    for month in range(1, 1201):
        contribution = 1_000_000 if 5 <= month <= 7 else 5_000_000
        balance = balance * (1 + rate) + contribution
        if month <= 24:
            row = result["stressed"]["monthly_projection"][month]
            assert row["balance"] == pytest.approx(balance, abs=0.001)
            assert row["target_amount"] == pytest.approx(120_000_000 * (1 + inf) ** month)
        if first is None and balance >= 120_000_000 * (1 + inf) ** month:
            first = month
        if month >= 24 and first is not None:
            break
    assert result["stressed"]["calculation_result"]["estimated_month_to_goal"] == first
    # Verify the reported recovery PMT actually reaches the original inflated goal.
    c = result["comparison"]
    end_balance = result["stressed"]["monthly_projection"][7]["balance"]
    rp = {**profile, "current_savings": end_balance + 20_000_000, "goal_horizon_months": 17,
          "goal_amount": result["baseline"]["calculation_result"]["adjusted_goal_amount"]}
    recovery = calculate_financial_metrics(rp, {"annual_return_rate": 0.06,
                                                "monthly_contribution": c["recovery_required_monthly_contribution"]})
    assert recovery["goal_gap"] == pytest.approx(0, abs=0.01)


def test_no_shock_matches_baseline_with_interest_and_inflation(profile):
    result = run_stress_test(profile, {"annual_return_rate": 0.04, "annual_inflation_rate": 0.02},
                             {"income_reduction_rate": 0})
    assert result["comparison"]["fv_total_reduction"] == pytest.approx(0, abs=0.001)
    assert result["comparison"]["goal_delay_months"] == 0


@pytest.mark.parametrize("rate", [0.01, 0.04, 0.06])
def test_zero_shock_at_exact_goal_never_flips_achievement(profile, rate):
    assumptions = {"annual_return_rate": rate}
    profile["goal_amount"] = calculate_financial_metrics(profile, assumptions)["fv_total"]
    result = run_stress_test(profile, assumptions, {"income_reduction_rate": 0})
    before, after = result["baseline"]["calculation_result"], result["stressed"]["calculation_result"]
    assert after["fv_total"] == before["fv_total"]
    assert after["goal_gap"] == before["goal_gap"] == 0
    assert after["goal_reached_by_horizon"] is before["goal_reached_by_horizon"] is True
    assert after["estimated_month_to_goal"] == before["estimated_month_to_goal"]


def test_invalid_config_is_controlled(profile, monkeypatch, tmp_path):
    import src.scenarios as module
    config = load_scenario_defaults()
    config["limits"]["max_projection_months"] = "1200"
    path = tmp_path / "scenario_defaults.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(module, "CONFIG_PATH", path)
    with pytest.raises(ScenarioInputError):
        build_scenarios(profile, {"annual_return_rate": 0})


def test_shock_absorbed_by_unallocated_surplus(profile):
    result = run_stress_test(profile, {"annual_return_rate": 0, "monthly_contribution": 500_000}, {})
    assert result["comparison"]["fv_total_reduction"] == 0
    assert result["stressed"]["monthly_projection"][1]["monthly_contribution"] == 500_000


def test_cashflow_deficit_does_not_consume_emergency_fund(profile):
    result = run_stress_test(profile, {"annual_return_rate": 0}, {"income_reduction_rate": 1})
    assert result["comparison"]["unfunded_cashflow_deficit"] == 45_000_000
    assert result["stressed"]["emergency_fund_available"] == 20_000_000
    assert result["stressed"]["monthly_projection"][1]["balance"] == 10_000_000
    assert "unfunded_cashflow_deficit_not_deducted_from_goal_or_emergency_fund" in result["stressed"]["warnings"]


def test_negative_baseline_cashflow_is_warning_not_negative_deposit(profile):
    profile["monthly_essential_expense"] = 25_000_000
    result = build_scenarios(profile, {"annual_return_rate": 0})
    assert result["base"]["calculation_result"]["monthly_contribution"] == 0
    assert "negative_monthly_cash_flow" in result["base"]["warnings"]


def test_one_month_horizon_applies_only_one_shocked_month(profile):
    profile["goal_horizon_months"] = 1
    result = run_stress_test(profile, {"annual_return_rate": 0}, {})
    assert len(result["stressed"]["monthly_projection"]) == 2
    assert result["stressed"]["calculation_result"]["fv_total"] == 11_000_000
    assert result["comparison"]["recovery_required_monthly_contribution"] is None
    assert result["comparison"]["fv_total_reduction"] == 4_000_000


def test_goal_already_reached_and_reserve_shortfall(profile):
    profile["goal_amount"] = 5_000_000
    result = run_stress_test(profile, {"annual_return_rate": 0}, {})
    assert result["stressed"]["calculation_result"]["estimated_month_to_goal"] == 0
    profile["current_savings"] = 5_000_000
    item = build_scenarios(profile, {"annual_return_rate": 0})["base"]
    assert item["calculation_result"]["initial_available_amount"] == 0
    assert item["emergency_fund_available"] == 5_000_000
    assert "emergency_fund_reserved_exceeds_current_savings" in item["warnings"]


def test_unreached_timing_is_none_not_zero(profile):
    profile["goal_amount"] = 1_000_000_000_000
    result = run_stress_test(profile, {"annual_return_rate": 0, "max_projection_months": 24}, {})
    assert result["stressed"]["calculation_result"]["estimated_month_to_goal"] is None
    assert result["comparison"]["goal_delay_months"] is None


@pytest.mark.parametrize("config", [
    {"income_reduction_rate": -0.2}, {"income_reduction_rate": 1.1},
    {"duration_months": 0}, {"duration_months": 1.5},
    {"start_month": 0}, {"start_month": 25}, {"unexpected": 1},
])
def test_invalid_stress_config_is_controlled(profile, config):
    with pytest.raises(ScenarioInputError):
        run_stress_test(profile, {"annual_return_rate": 0}, config)


def test_charts_accept_mock_results_without_calculation(monkeypatch):
    pytest.importorskip("plotly")
    import src.scenarios as module
    monkeypatch.setattr(module, "calculate_financial_metrics", lambda *a, **k: pytest.fail("chart must not call engine"))
    mock = {}
    for key, value in [("conservative", 80), ("base", 100), ("optimistic", 120)]:
        mock[key] = {"label": key, "calculation_result": {
            "fv_total": value, "adjusted_goal_amount": 100, "goal_gap": 100 - value,
            "goal_reached_by_horizon": value >= 100, "estimated_month_to_goal": 1 if value >= 100 else None,
            "monthly_contribution": value, "required_monthly_contribution": 100},
            "monthly_projection": [{"month": 0, "balance": 0, "target_amount": 100},
                                   {"month": 1, "balance": value, "target_amount": 100}],
            "emergency_fund_available": 20, "total_contributions": value, "investment_gain": 0}
    before = deepcopy(mock)
    table = build_comparison_table(mock)
    assert table.loc["fv_total", "base"] == 100
    assert len(create_balance_chart(mock).data) == 6
    assert list(create_final_value_chart(mock).data[0].y) == [80, 100, 120]
    assert mock == before
    mock["base"]["monthly_projection"][-1]["balance"] = 999
    with pytest.raises(ScenarioInputError):
        create_balance_chart(mock)


def test_chart_targets_follow_each_what_if_horizon(profile):
    pytest.importorskip("plotly")
    r = run_what_if(profile, {"annual_return_rate": 0, "annual_inflation_rate": 0.03}, {"goal_horizon_months": 36})
    fig = create_balance_chart(r)
    assert len(fig.data[0].x) == 25
    assert len(fig.data[2].x) == 37
    assert fig.data[3].y[-1] > fig.data[1].y[-1]


def _app(profile, *, demo=True, status=None, confirmed=False):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    source = (
        "import streamlit as st\n"
        "from ui.scenario_page import render_scenario_page\n"
        f"result = render_scenario_page({profile!r}, {{'annual_return_rate': 0.0}}, "
        f"demo_mode={demo!r}, validation_status={status!r}, profile_confirmed={confirmed!r})\n"
        "st.session_state['test_result'] = result\n"
    )
    return AppTest.from_string(source, default_timeout=30).run()


def test_ui_requires_real_validation_and_profile_confirmation(profile):
    at = _app(profile, demo=False)
    assert not at.exception
    assert at.session_state["test_result"] is None
    assert len(at.info) == 1
    at = _app(profile, demo=False, status="OUT_OF_SCOPE", confirmed=True)
    assert at.session_state["test_result"] is None


def test_ui_confirm_edit_reset_and_stress(profile):
    at = _app(profile)
    assert not at.exception
    assert at.session_state["test_result"] is None
    at.checkbox(key="person3_profile_confirmed").check().run()
    at.checkbox(key="person3_assumptions_confirmed").check().run()
    assert not at.exception
    assert not at.error
    assert at.session_state["test_result"]["stress_test"]["stressed"]["calculation_result"]["fv_total"] == 118_000_000
    at.number_input(key="person3_wi_monthly_primary_income").set_value(19_000_000.0).run()
    assert not at.exception
    assert not at.checkbox(key="person3_assumptions_confirmed").value
    at.checkbox(key="person3_assumptions_confirmed").check().run()
    assert at.session_state["test_result"]["what_if"]["modified"]["calculation_result"]["monthly_contribution"] == 6_000_000
    at.button(key="person3_reset").click().run()
    assert not at.exception
    assert at.session_state["test_result"] is None
    at.checkbox(key="person3_profile_confirmed").check().run()
    at.checkbox(key="person3_assumptions_confirmed").check().run()
    assert at.number_input(key="person3_wi_monthly_primary_income").value == 18_000_000.0


def test_ui_assumptions_change_recalculates_without_extra_confirmation(profile):
    at = _app(profile, demo=False, status="VALID", confirmed=True)
    assert at.session_state["test_result"] is not None
    at.number_input(key="person3_return").set_value(2.0).run()
    assert not at.exception
    assert at.session_state["test_result"] is not None
    assert at.session_state["test_result"]["scenarios"]["base"]["assumptions"]["annual_return_rate"] == 0.02


def test_ui_bad_profile_displays_controlled_error(profile):
    profile["goal_horizon_months"] = None
    at = _app(profile, demo=False, status="VALID", confirmed=True)
    assert not at.exception
    assert len(at.error) == 1
