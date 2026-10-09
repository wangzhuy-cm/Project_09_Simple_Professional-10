"""Financial calculation engine for Project 09 (Person 2).

All monetary calculations are performed in Python.  This module does not call
an LLM and does not implement Person 4's validation statuses or Person 3's
scenario/stress-test logic.

Contract
--------
``calculate_financial_metrics(profile: dict, assumptions: dict) -> dict``

The function never mutates ``profile`` or ``assumptions``.  Rates supplied in
``assumptions`` are annual decimal rates and are converted to effective monthly
rates using ``(1 + annual_rate) ** (1/12) - 1``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


_REQUIRED_PROFILE_FIELDS = (
    "monthly_primary_income",
    "monthly_other_income",
    "monthly_essential_expense",
    "monthly_discretionary_expense",
    "monthly_debt_payment",
    "current_savings",
    "emergency_fund_reserved",
    "goal_amount",
    "goal_horizon_months",
)


class CalculationInputError(ValueError):
    """Raised when the calculation engine cannot safely calculate from input."""


def annual_to_monthly_rate(annual_rate: float) -> float:
    """Convert an annual effective decimal rate to an effective monthly rate.

    Args:
        annual_rate: Annual decimal rate, e.g. ``0.06`` for 6%.

    Returns:
        Effective monthly decimal rate.

    Raises:
        CalculationInputError: If the value is non-numeric, non-finite, or
            less than or equal to -100%, for which the fractional power is not
            meaningful in this MVP.
    """

    rate = _finite_number(annual_rate, "annual_rate")
    if rate <= -1.0:
        raise CalculationInputError("annual_rate must be greater than -1.0")
    return (1.0 + rate) ** (1.0 / 12.0) - 1.0


def _finite_number(value: Any, field_name: str) -> float:
    if value is None:
        raise CalculationInputError(f"{field_name} is required for calculation")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalculationInputError(f"{field_name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise CalculationInputError(f"{field_name} must be a finite number")
    return number


def _month_count(value: Any) -> int:
    if value is None:
        raise CalculationInputError("goal_horizon_months is required for calculation")
    if isinstance(value, bool) or not isinstance(value, int):
        raise CalculationInputError("goal_horizon_months must be an integer")
    if value <= 0:
        raise CalculationInputError("goal_horizon_months must be greater than 0")
    return value


def _future_value_initial(present_value: float, monthly_rate: float, months: int) -> float:
    return present_value * (1.0 + monthly_rate) ** months


def _annuity_factor(monthly_rate: float, months: int) -> float:
    if months <= 0:
        raise CalculationInputError("months must be greater than 0")
    if math.isclose(monthly_rate, 0.0, abs_tol=1e-15):
        return float(months)
    return ((1.0 + monthly_rate) ** months - 1.0) / monthly_rate


def _future_value_contribution(monthly_contribution: float, monthly_rate: float, months: int) -> float:
    return monthly_contribution * _annuity_factor(monthly_rate, months)


def _required_monthly_contribution(
    target_amount: float,
    future_value_initial: float,
    monthly_rate: float,
    months: int,
) -> float:
    remaining = target_amount - future_value_initial
    if remaining <= 0:
        return 0.0
    factor = _annuity_factor(monthly_rate, months)
    if factor <= 0:
        raise CalculationInputError("annuity factor must be positive")
    return remaining / factor


def _estimated_month_to_goal(
    initial_amount: float,
    monthly_contribution: float,
    monthly_return_rate: float,
    nominal_goal_amount: float,
    monthly_inflation_rate: float,
    max_months: int,
) -> int | None:
    """Simulate end-of-month contributions until the goal is reached.

    Inflation, when enabled, increases the target each month.  Returns month 0
    when the initial amount already meets the current nominal goal.
    """

    balance = initial_amount
    if balance >= nominal_goal_amount:
        return 0

    for month in range(1, max_months + 1):
        balance = balance * (1.0 + monthly_return_rate) + monthly_contribution
        target = nominal_goal_amount * (1.0 + monthly_inflation_rate) ** month
        if balance >= target:
            return month
    return None


def calculate_financial_metrics(profile: dict, assumptions: dict) -> dict:
    """Calculate Project 09's core monthly cash-flow and goal metrics.

    Args:
        profile: FinancialProfile-compatible mapping.  The engine requires the
            numeric fields listed in ``_REQUIRED_PROFILE_FIELDS`` to be present
            and non-null.  Business validation should normally be performed by
            Person 4 before calling this function.
        assumptions: Mapping with ``annual_return_rate`` (required). Optional
            keys are ``monthly_contribution`` (defaults to non-negative monthly
            surplus), ``annual_inflation_rate`` (defaults to 0.0), and
            ``max_projection_months`` (defaults to max(goal horizon, 1200)).

    Returns:
        A newly allocated dictionary with English keys containing cash-flow,
        affordability gaps, future-value, goal-gap, required-contribution,
        timing, assumptions and calculation warnings.

    Raises:
        TypeError: If ``profile`` or ``assumptions`` is not a mapping/dict-like
            object.
        CalculationInputError: If required calculation data is missing or has
            an unsafe structural/numeric value.
    """

    if not isinstance(profile, Mapping):
        raise TypeError("profile must be a mapping")
    if not isinstance(assumptions, Mapping):
        raise TypeError("assumptions must be a mapping")

    for field in _REQUIRED_PROFILE_FIELDS:
        if field not in profile:
            raise CalculationInputError(f"missing profile field: {field}")
        if profile[field] is None:
            raise CalculationInputError(f"{field} is required for calculation")

    primary_income = _finite_number(profile["monthly_primary_income"], "monthly_primary_income")
    other_income = _finite_number(profile["monthly_other_income"], "monthly_other_income")
    essential_expense = _finite_number(profile["monthly_essential_expense"], "monthly_essential_expense")
    discretionary_expense = _finite_number(profile["monthly_discretionary_expense"], "monthly_discretionary_expense")
    debt_payment = _finite_number(profile["monthly_debt_payment"], "monthly_debt_payment")
    current_savings = _finite_number(profile["current_savings"], "current_savings")
    emergency_reserved = _finite_number(profile["emergency_fund_reserved"], "emergency_fund_reserved")
    goal_amount = _finite_number(profile["goal_amount"], "goal_amount")
    horizon = _month_count(profile["goal_horizon_months"])

    if goal_amount <= 0:
        raise CalculationInputError("goal_amount must be greater than 0")

    if "annual_return_rate" not in assumptions:
        raise CalculationInputError("annual_return_rate is required in assumptions")
    annual_return_rate = _finite_number(assumptions["annual_return_rate"], "annual_return_rate")
    monthly_return_rate = annual_to_monthly_rate(annual_return_rate)

    annual_inflation_rate = _finite_number(
        assumptions.get("annual_inflation_rate", 0.0), "annual_inflation_rate"
    )
    monthly_inflation_rate = annual_to_monthly_rate(annual_inflation_rate)

    total_monthly_income = primary_income + other_income
    total_monthly_outflow = essential_expense + discretionary_expense + debt_payment
    monthly_surplus = total_monthly_income - total_monthly_outflow

    if math.isclose(total_monthly_income, 0.0, abs_tol=1e-12):
        savings_rate: float | None = None
    else:
        savings_rate = monthly_surplus / total_monthly_income

    raw_initial_available = current_savings - emergency_reserved
    initial_available_amount = max(raw_initial_available, 0.0)

    if "monthly_contribution" in assumptions and assumptions["monthly_contribution"] is not None:
        monthly_contribution = _finite_number(
            assumptions["monthly_contribution"], "monthly_contribution"
        )
        contribution_source = "assumption"
    else:
        monthly_contribution = max(monthly_surplus, 0.0)
        contribution_source = "non_negative_monthly_surplus"

    if monthly_contribution < 0:
        raise CalculationInputError("monthly_contribution must not be negative")

    adjusted_goal_amount = goal_amount * (1.0 + monthly_inflation_rate) ** horizon
    fv_initial = _future_value_initial(initial_available_amount, monthly_return_rate, horizon)
    fv_contribution = _future_value_contribution(monthly_contribution, monthly_return_rate, horizon)
    fv_total = fv_initial + fv_contribution
    goal_gap = adjusted_goal_amount - fv_total
    required_monthly_contribution = _required_monthly_contribution(
        adjusted_goal_amount, fv_initial, monthly_return_rate, horizon
    )

    affordable_monthly_contribution = max(monthly_surplus, 0.0)
    contribution_affordability_gap = max(
        monthly_contribution - affordable_monthly_contribution, 0.0
    )
    required_contribution_gap = max(
        required_monthly_contribution - affordable_monthly_contribution, 0.0
    )

    max_projection_months_raw = assumptions.get("max_projection_months", max(horizon, 1200))
    if isinstance(max_projection_months_raw, bool) or not isinstance(max_projection_months_raw, int):
        raise CalculationInputError("max_projection_months must be an integer")
    if max_projection_months_raw <= 0:
        raise CalculationInputError("max_projection_months must be greater than 0")

    estimated_month_to_goal = _estimated_month_to_goal(
        initial_amount=initial_available_amount,
        monthly_contribution=monthly_contribution,
        monthly_return_rate=monthly_return_rate,
        nominal_goal_amount=goal_amount,
        monthly_inflation_rate=monthly_inflation_rate,
        max_months=max_projection_months_raw,
    )

    warnings: list[str] = []
    if raw_initial_available < 0:
        warnings.append("emergency_fund_reserved_exceeds_current_savings")
    if monthly_surplus < 0:
        warnings.append("negative_monthly_cash_flow")
    if savings_rate is None:
        warnings.append("savings_rate_unavailable_zero_income")
    if initial_available_amount >= goal_amount:
        warnings.append("goal_already_funded_from_available_savings")
    if contribution_affordability_gap > 0:
        warnings.append("monthly_contribution_exceeds_current_surplus")
    if required_contribution_gap > 0:
        warnings.append("required_monthly_contribution_exceeds_current_surplus")
    if estimated_month_to_goal is None:
        warnings.append("goal_not_reached_within_projection_limit")

    return {
        "total_monthly_income": total_monthly_income,
        "total_monthly_outflow": total_monthly_outflow,
        "monthly_surplus": monthly_surplus,
        "savings_rate": savings_rate,
        "initial_available_amount": initial_available_amount,
        "monthly_contribution": monthly_contribution,
        "contribution_source": contribution_source,
        "affordable_monthly_contribution": affordable_monthly_contribution,
        "contribution_affordability_gap": contribution_affordability_gap,
        "annual_return_rate": annual_return_rate,
        "monthly_return_rate": monthly_return_rate,
        "annual_inflation_rate": annual_inflation_rate,
        "monthly_inflation_rate": monthly_inflation_rate,
        "nominal_goal_amount": goal_amount,
        "adjusted_goal_amount": adjusted_goal_amount,
        "goal_horizon_months": horizon,
        "fv_initial": fv_initial,
        "fv_contribution": fv_contribution,
        "fv_total": fv_total,
        "goal_gap": goal_gap,
        "goal_reached_by_horizon": goal_gap <= 0,
        "required_monthly_contribution": required_monthly_contribution,
        "required_contribution_gap": required_contribution_gap,
        "estimated_month_to_goal": estimated_month_to_goal,
        "calculation_warnings": warnings,
        "assumptions_used": {
            "contribution_timing": "end_of_month",
            "return_rate_basis": "annual_effective_converted_to_monthly_effective",
            "inflation_enabled": not math.isclose(annual_inflation_rate, 0.0, abs_tol=1e-15),
            "taxes_and_fees_included": False,
        },
    }


__all__ = [
    "CalculationInputError",
    "annual_to_monthly_rate",
    "calculate_financial_metrics",
]
