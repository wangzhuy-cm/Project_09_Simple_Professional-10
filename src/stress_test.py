"""Person 3: temporary income shock using only the public Person 2 engine."""
from __future__ import annotations

from copy import deepcopy

from src.scenarios import (ScenarioInputError, call_engine, finite_number,
                           load_scenario_defaults, prepare_inputs, project_scenario)


def _stress_config(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ScenarioInputError("stress_config phải là dict.")
    config = deepcopy(load_scenario_defaults()["stress_defaults"])
    if set(raw) - set(config):
        raise ScenarioInputError("stress_config có khóa chưa được hỗ trợ.")
    config.update(deepcopy(raw))
    rate = finite_number(config["income_reduction_rate"], "income_reduction_rate", 0)
    if rate > 1:
        raise ScenarioInputError("income_reduction_rate phải nằm trong [0, 1].")
    for field in ("start_month", "duration_months"):
        value = config[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ScenarioInputError(f"{field} phải là số nguyên dương.")
    return config


def run_stress_test(profile: dict, base_assumptions: dict, stress_config: dict) -> dict:
    """Return baseline/stressed/comparison for a temporary reduction of both incomes.

    Empty stress_config means 20% less income in months 1--3. Expenses/debt and
    annual return stay unchanged. During affected months the actual contribution
    is min(planned contribution, non-negative stressed surplus). Afterwards the
    planned contribution resumes. A one-month engine call advances each balance
    and inflation-adjusted target; no financial-engine formula is duplicated.

    Cash-flow deficits are reported separately, never silently funded from savings
    or the emergency reserve. Therefore results are conditional projections if
    deficits/over-budget contributions exist. Recovery uses the public engine to
    solve a CONSTANT contribution AFTER the shock until the original deadline.
    None timing means not reached within the configured projection limit.

    Raises ScenarioInputError for invalid profile, assumptions or shock options.
    No caller-owned object is mutated; this function does not perform Person 4's
    validation or human confirmation and does not produce a final report.
    """
    p, a = prepare_inputs(profile, base_assumptions)
    config = _stress_config(stress_config)
    horizon = p["goal_horizon_months"]
    maximum = a.get("max_projection_months", 1200)
    start, duration = config["start_month"], config["duration_months"]
    if start > horizon:
        raise ScenarioInputError("start_month phải nằm trong thời hạn mục tiêu.")
    end = start + duration - 1
    if end > maximum:
        raise ScenarioInputError("Khoảng stress vượt max_projection_months.")
    baseline = project_scenario(p, a, name="baseline", label="Trước stress")
    bm = baseline["calculation_result"]
    planned = bm["monthly_contribution"]
    balance, target = bm["initial_available_amount"], p["goal_amount"]
    cumulative, total_cashflow_deficit = 0.0, 0.0
    estimated = 0 if balance >= target else None
    records = [{"month": 0, "balance": balance, "target_amount": target,
                "monthly_contribution": 0.0, "cumulative_contributions": 0.0,
                "total_monthly_income": bm["total_monthly_income"],
                "monthly_surplus": bm["monthly_surplus"], "cashflow_deficit": 0.0,
                "contribution_affordability_gap": 0.0, "stress_active": False}]
    warnings = list(baseline["warnings"])
    balance_at_end_of_stress = None
    horizon_metrics = None
    for month in range(1, maximum + 1):
        affected = start <= month <= end
        step_profile = deepcopy(p)
        if affected:
            for field in ("monthly_primary_income", "monthly_other_income"):
                step_profile[field] *= 1.0 - config["income_reduction_rate"]
        # This synthetic engine input carries only the goal bucket forward.
        # It does not change the user's actual savings or reserved funds.
        step_profile["current_savings"] = balance + p["emergency_fund_reserved"]
        step_profile["goal_amount"] = target
        step_profile["goal_horizon_months"] = 1
        step_assumptions = deepcopy(a)
        step_assumptions["max_projection_months"] = 1
        step_assumptions["monthly_contribution"] = None
        capacity = call_engine(step_profile, step_assumptions)
        contribution = planned
        if affected and config["income_reduction_rate"] > 0:
            contribution = min(planned, capacity["affordable_monthly_contribution"])
        step_assumptions["monthly_contribution"] = contribution
        step = call_engine(step_profile, step_assumptions)
        balance, target = step["fv_total"], step["adjusted_goal_amount"]
        cumulative += contribution
        if estimated is None and balance >= target:
            estimated = month
        cashflow_deficit = max(-step["monthly_surplus"], 0.0)
        if month <= horizon:
            total_cashflow_deficit += cashflow_deficit
            records.append({
                "month": month, "balance": balance, "target_amount": target,
                "monthly_contribution": contribution, "cumulative_contributions": cumulative,
                "total_monthly_income": step["total_monthly_income"],
                "monthly_surplus": step["monthly_surplus"], "cashflow_deficit": cashflow_deficit,
                "contribution_affordability_gap": step["contribution_affordability_gap"],
                "stress_active": affected,
            })
        if month == end:
            balance_at_end_of_stress = balance
        if month == horizon:
            horizon_metrics = {
                "fv_total": balance, "adjusted_goal_amount": target, "goal_gap": target - balance,
                "goal_reached_by_horizon": balance >= target,
                "fv_initial": bm["fv_initial"], "fv_contribution": balance - bm["fv_initial"],
            }
        if month >= horizon and estimated is not None:
            break
    assert horizon_metrics is not None
    # Same schedule must have EXACTLY the same reported outcome as Person 2.
    # Repeated one-month calls can differ from closed-form FV by a few ULPs;
    # without this identity rule, a zero shock could flip the goal-reached flag.
    if all(row["monthly_contribution"] == planned for row in records[1:]):
        for row, source_row in zip(records, baseline["monthly_projection"]):
            for field in ("balance", "target_amount", "cumulative_contributions"):
                row[field] = source_row[field]
        for field in tuple(horizon_metrics):
            horizon_metrics[field] = bm[field]
        estimated = bm["estimated_month_to_goal"]
        if end <= horizon:
            balance_at_end_of_stress = records[end]["balance"]
    else:
        # The final target belongs to the original deadline, independent of shock.
        horizon_metrics["adjusted_goal_amount"] = bm["adjusted_goal_amount"]
        horizon_metrics["goal_gap"] = bm["adjusted_goal_amount"] - horizon_metrics["fv_total"]
        horizon_metrics["goal_reached_by_horizon"] = horizon_metrics["goal_gap"] <= 0
        records[-1]["target_amount"] = bm["adjusted_goal_amount"]
    if end > horizon:
        warnings.append("stress_window_truncated_at_goal_horizon_for_final_balance")
    if total_cashflow_deficit > 0:
        warnings.append("unfunded_cashflow_deficit_not_deducted_from_goal_or_emergency_fund")
    if any(row["contribution_affordability_gap"] > 0 for row in records):
        warnings.append("monthly_contribution_exceeds_current_surplus")
    if estimated is None:
        warnings.append("goal_not_reached_within_projection_limit")
    warnings = list(dict.fromkeys(warnings))
    old_month = bm["estimated_month_to_goal"]
    timing_change = None if old_month is None or estimated is None else estimated - old_month

    recovery_required = recovery_additional = recovery_gap = None
    if end < horizon and balance_at_end_of_stress is not None:
        rp, ra = deepcopy(p), deepcopy(a)
        rp["current_savings"] = balance_at_end_of_stress + p["emergency_fund_reserved"]
        rp["goal_horizon_months"] = horizon - end
        # The final target already includes inflation to the original deadline.
        rp["goal_amount"] = bm["adjusted_goal_amount"]
        ra["annual_inflation_rate"] = 0.0
        ra["monthly_contribution"] = planned
        recovery = call_engine(rp, ra)
        recovery_required = recovery["required_monthly_contribution"]
        recovery_additional = max(recovery_required - planned, 0.0)
        recovery_gap = recovery["required_contribution_gap"]

    horizon_metrics.update({
        "estimated_month_to_goal": estimated,
        "initial_available_amount": bm["initial_available_amount"],
        "nominal_goal_amount": bm["nominal_goal_amount"],
        "goal_horizon_months": horizon,
        "annual_return_rate": bm["annual_return_rate"],
        "monthly_return_rate": bm["monthly_return_rate"],
        "annual_inflation_rate": bm["annual_inflation_rate"],
        "monthly_inflation_rate": bm["monthly_inflation_rate"],
        # No single fixed PMT or single monthly surplus describes this schedule.
        "monthly_contribution": None, "required_monthly_contribution": None,
        "contribution_source": "temporary_income_shock_schedule",
        "calculation_warnings": warnings,
        "assumptions_used": {**bm["assumptions_used"], "variable_contribution_schedule": True},
    })
    stressed = {
        "scenario_name": "stressed", "label": "Sau stress",
        "profile_used": deepcopy(p), "assumptions": deepcopy(a),
        "calculation_result": horizon_metrics, "monthly_projection": records,
        "planned_monthly_contribution": planned,
        "total_contributions": records[-1]["cumulative_contributions"],
        "investment_gain": horizon_metrics["fv_total"] - bm["initial_available_amount"] - records[-1]["cumulative_contributions"],
        "emergency_fund_reserved": p["emergency_fund_reserved"],
        "emergency_fund_available": baseline["emergency_fund_available"],
        "unfunded_cashflow_deficit": total_cashflow_deficit,
        "warnings": warnings,
    }
    return {
        "baseline": baseline, "stressed": stressed, "stress_config": config,
        "comparison": {
            "fv_total_reduction": bm["fv_total"] - horizon_metrics["fv_total"],
            "goal_gap_increase": horizon_metrics["goal_gap"] - bm["goal_gap"],
            "month_to_goal_change": timing_change,
            "goal_delay_months": None if timing_change is None else max(timing_change, 0),
            "baseline_goal_reached_by_horizon": bm["goal_reached_by_horizon"],
            "stressed_goal_reached_by_horizon": horizon_metrics["goal_reached_by_horizon"],
            "extension_months_from_original_horizon": None if estimated is None else max(estimated - horizon, 0),
            "recovery_start_month": end + 1 if end < horizon else None,
            "recovery_required_monthly_contribution": recovery_required,
            "additional_monthly_contribution_after_stress": recovery_additional,
            "recovery_required_contribution_gap": recovery_gap,
            "recovery_unavailable_reason": None if recovery_required is not None else "no_months_after_stress_before_deadline",
            "unfunded_cashflow_deficit": total_cashflow_deficit,
        },
        "metadata": {"currency": "VND", "max_projection_months": maximum,
                     "emergency_fund_drawdown_modelled": False,
                     "deficit_funding_modelled": False, "is_final_plan": False},
    }
