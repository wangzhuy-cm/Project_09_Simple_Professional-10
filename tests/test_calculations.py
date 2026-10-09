from __future__ import annotations

import copy
import math

import pytest

from src.calculations import (
    CalculationInputError,
    annual_to_monthly_rate,
    calculate_financial_metrics,
)
def load_p001() -> dict:
    """Standalone mock matching Person 1's 15-key FinancialProfile contract."""
    return {
        "user_id": "P001",
        "monthly_primary_income": 8_000_000.0,
        "monthly_other_income": 2_000_000.0,
        "monthly_essential_expense": 5_000_000.0,
        "monthly_discretionary_expense": 2_000_000.0,
        "monthly_debt_payment": 0.0,
        "current_savings": 15_000_000.0,
        "emergency_fund_reserved": 5_000_000.0,
        "goal_name": "Higher education",
        "goal_amount": 100_000_000.0,
        "goal_horizon_months": 36,
        "risk_tolerance": "low",
        "liquidity_need": "medium",
        "expected_income_growth": 0.05,
        "notes": None,
    }


def test_p001_zero_return_baseline() -> None:
    result = calculate_financial_metrics(load_p001(), {"annual_return_rate": 0.0})

    assert result["total_monthly_income"] == pytest.approx(10_000_000)
    assert result["total_monthly_outflow"] == pytest.approx(7_000_000)
    assert result["monthly_surplus"] == pytest.approx(3_000_000)
    assert result["savings_rate"] == pytest.approx(0.30)
    assert result["initial_available_amount"] == pytest.approx(10_000_000)
    assert result["monthly_contribution"] == pytest.approx(3_000_000)
    assert result["fv_initial"] == pytest.approx(10_000_000)
    assert result["fv_contribution"] == pytest.approx(108_000_000)
    assert result["fv_total"] == pytest.approx(118_000_000)
    assert result["goal_gap"] == pytest.approx(-18_000_000)
    assert result["required_monthly_contribution"] == pytest.approx(2_500_000)
    assert result["estimated_month_to_goal"] == 30
    assert result["goal_reached_by_horizon"] is True


def test_annual_to_monthly_effective_rate() -> None:
    monthly = annual_to_monthly_rate(0.12)
    assert (1 + monthly) ** 12 == pytest.approx(1.12)


def test_nonzero_return_future_value_matches_formula() -> None:
    profile = load_p001()
    annual_rate = 0.06
    result = calculate_financial_metrics(
        profile,
        {"annual_return_rate": annual_rate, "monthly_contribution": 2_500_000},
    )
    i = (1 + annual_rate) ** (1 / 12) - 1
    n = profile["goal_horizon_months"]
    expected_initial = 10_000_000 * (1 + i) ** n
    expected_contrib = 2_500_000 * (((1 + i) ** n - 1) / i)
    assert result["fv_initial"] == pytest.approx(expected_initial)
    assert result["fv_contribution"] == pytest.approx(expected_contrib)
    assert result["fv_total"] == pytest.approx(expected_initial + expected_contrib)


def test_zero_return_avoids_division_by_zero() -> None:
    profile = load_p001()
    profile["goal_horizon_months"] = 1
    result = calculate_financial_metrics(
        profile,
        {"annual_return_rate": 0.0, "monthly_contribution": 3_000_000},
    )
    assert result["fv_contribution"] == pytest.approx(3_000_000)


def test_one_month_horizon_required_contribution() -> None:
    profile = load_p001()
    profile["goal_amount"] = 20_000_000
    profile["goal_horizon_months"] = 1
    result = calculate_financial_metrics(profile, {"annual_return_rate": 0.0})
    assert result["required_monthly_contribution"] == pytest.approx(10_000_000)


def test_negative_cash_flow_is_calculated_but_not_used_as_default_contribution() -> None:
    profile = load_p001()
    profile["monthly_essential_expense"] = 12_000_000
    result = calculate_financial_metrics(profile, {"annual_return_rate": 0.0})
    assert result["monthly_surplus"] == pytest.approx(-4_000_000)
    assert result["monthly_contribution"] == 0.0
    assert "negative_monthly_cash_flow" in result["calculation_warnings"]


def test_goal_already_achieved_from_available_savings() -> None:
    profile = load_p001()
    profile["current_savings"] = 120_000_000
    profile["emergency_fund_reserved"] = 5_000_000
    result = calculate_financial_metrics(profile, {"annual_return_rate": 0.0})
    assert result["required_monthly_contribution"] == 0.0
    assert result["estimated_month_to_goal"] == 0
    assert result["goal_reached_by_horizon"] is True


def test_emergency_fund_shortfall_clamps_available_amount_to_zero() -> None:
    profile = load_p001()
    profile["current_savings"] = 3_000_000
    profile["emergency_fund_reserved"] = 5_000_000
    result = calculate_financial_metrics(profile, {"annual_return_rate": 0.0})
    assert result["initial_available_amount"] == 0.0
    assert "emergency_fund_reserved_exceeds_current_savings" in result["calculation_warnings"]


def test_zero_income_savings_rate_is_none() -> None:
    profile = load_p001()
    profile["monthly_primary_income"] = 0
    profile["monthly_other_income"] = 0
    profile["monthly_essential_expense"] = 0
    profile["monthly_discretionary_expense"] = 0
    result = calculate_financial_metrics(profile, {"annual_return_rate": 0.0})
    assert result["savings_rate"] is None
    assert "savings_rate_unavailable_zero_income" in result["calculation_warnings"]


def test_missing_required_profile_value_fails_cleanly() -> None:
    profile = load_p001()
    profile["goal_horizon_months"] = None
    with pytest.raises(CalculationInputError, match="goal_horizon_months"):
        calculate_financial_metrics(profile, {"annual_return_rate": 0.0})


def test_missing_return_assumption_fails_cleanly() -> None:
    with pytest.raises(CalculationInputError, match="annual_return_rate"):
        calculate_financial_metrics(load_p001(), {})


def test_invalid_annual_rate_fails_cleanly() -> None:
    with pytest.raises(CalculationInputError, match="greater than -1.0"):
        calculate_financial_metrics(load_p001(), {"annual_return_rate": -1.0})


def test_inputs_are_not_mutated() -> None:
    profile = load_p001()
    assumptions = {"annual_return_rate": 0.05, "monthly_contribution": 2_000_000}
    profile_before = copy.deepcopy(profile)
    assumptions_before = copy.deepcopy(assumptions)
    calculate_financial_metrics(profile, assumptions)
    assert profile == profile_before
    assert assumptions == assumptions_before


def test_inflation_adjusts_goal_not_source_profile() -> None:
    profile = load_p001()
    result = calculate_financial_metrics(
        profile,
        {"annual_return_rate": 0.0, "annual_inflation_rate": 0.04},
    )
    assert result["adjusted_goal_amount"] > profile["goal_amount"]
    assert profile["goal_amount"] == 100_000_000


def test_explicit_monthly_contribution_overrides_surplus() -> None:
    result = calculate_financial_metrics(
        load_p001(),
        {"annual_return_rate": 0.0, "monthly_contribution": 1_500_000},
    )
    assert result["monthly_contribution"] == 1_500_000
    assert result["contribution_source"] == "assumption"
    assert result["fv_contribution"] == pytest.approx(54_000_000)


def test_explicit_contribution_above_surplus_is_flagged() -> None:
    result = calculate_financial_metrics(
        load_p001(),
        {"annual_return_rate": 0.0, "monthly_contribution": 5_000_000},
    )
    assert result["affordable_monthly_contribution"] == pytest.approx(3_000_000)
    assert result["contribution_affordability_gap"] == pytest.approx(2_000_000)
    assert "monthly_contribution_exceeds_current_surplus" in result["calculation_warnings"]


def test_required_contribution_gap_identifies_infeasible_current_cash_flow() -> None:
    profile = load_p001()
    profile["goal_amount"] = 200_000_000
    result = calculate_financial_metrics(profile, {"annual_return_rate": 0.0})
    expected_required = (200_000_000 - 10_000_000) / 36
    expected_gap = expected_required - 3_000_000
    assert result["required_monthly_contribution"] == pytest.approx(expected_required)
    assert result["required_contribution_gap"] == pytest.approx(expected_gap)
    assert "required_monthly_contribution_exceeds_current_surplus" in result["calculation_warnings"]


def test_no_affordability_warning_when_contribution_is_within_surplus() -> None:
    result = calculate_financial_metrics(
        load_p001(),
        {"annual_return_rate": 0.0, "monthly_contribution": 2_000_000},
    )
    assert result["contribution_affordability_gap"] == 0.0
    assert "monthly_contribution_exceeds_current_surplus" not in result["calculation_warnings"]
