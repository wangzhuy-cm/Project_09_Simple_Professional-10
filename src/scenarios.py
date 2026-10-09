"""Person 3: scenario orchestration only; financial formulas stay in Person 2.

Inputs are never mutated. The caller owns Person 4 validation and human review.
This module performs defensive checks, not the full business validation workflow.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
from typing import Any

from src.calculations import CalculationInputError, calculate_financial_metrics
from src.schemas import parse_financial_profile

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "scenario_defaults.json"
SCENARIO_NAMES = ("conservative", "base", "optimistic")
ENGINE_ASSUMPTIONS = frozenset({"annual_return_rate", "monthly_contribution",
                               "annual_inflation_rate", "max_projection_months"})
WHAT_IF_PROFILE_FIELDS = frozenset({
    "monthly_primary_income", "monthly_other_income", "monthly_essential_expense",
    "monthly_discretionary_expense", "monthly_debt_payment", "goal_amount",
    "goal_horizon_months",
})


class ScenarioInputError(ValueError):
    """Invalid input/configuration in Person 3; UI catches and displays this."""


def finite_number(value: Any, name: str, minimum: float | None = None) -> float:
    """Check a finite numeric input; raise ScenarioInputError on invalid values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScenarioInputError(f"{name}: cần số hữu hạn, không phải None/chuỗi/bool.")
    number = float(value)
    if not math.isfinite(number) or (minimum is not None and number < minimum):
        raise ScenarioInputError(f"{name}: giá trị ngoài phạm vi cho phép.")
    return number


def load_scenario_defaults() -> dict:
    """Read a fresh config; raise ScenarioInputError for missing/invalid JSON."""
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        limits = cfg["limits"]
        finite_number(limits["min_annual_return_rate"], "min_annual_return_rate")
        if limits["min_annual_return_rate"] <= -1:
            raise ValueError("minimum return must exceed -1")
        for risk in ("low", "medium", "high"):
            finite_number(limits["max_annual_return_rate_by_risk"][risk], risk,
                          limits["min_annual_return_rate"])
        minimum_inflation = finite_number(limits["min_annual_inflation_rate"], "min_annual_inflation_rate", 0)
        finite_number(limits["max_annual_inflation_rate"], "max_annual_inflation_rate", minimum_inflation)
        maximum = limits["max_projection_months"]
        if isinstance(maximum, bool) or not isinstance(maximum, int) or not 120 <= maximum <= 1200:
            raise ValueError("max_projection_months must be an integer from 120 to 1200")
        for name in SCENARIO_NAMES:
            row = cfg["scenarios"][name]
            for key in ("income_multiplier", "discretionary_expense_multiplier",
                        "contribution_multiplier"):
                finite_number(row[key], key, 0)
            finite_number(row["annual_return_rate_offset"], "annual_return_rate_offset")
            if not isinstance(row["label"], str):
                raise ValueError("label must be text")
        base = cfg["scenarios"]["base"]
        if any(base[k] != 1 for k in ("income_multiplier", "discretionary_expense_multiplier",
                                      "contribution_multiplier")) or base["annual_return_rate_offset"] != 0:
            raise ValueError("base scenario must preserve confirmed inputs")
        return cfg
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ScenarioInputError(f"Không đọc được cấu hình kịch bản: {exc}") from exc


def prepare_inputs(profile: dict, assumptions: dict) -> tuple[dict, dict]:
    """Copy/check canonical profile and engine options; raise ScenarioInputError.

Missing data is not converted to zero. Optional engine keys retain Person 2's
defaults (a missing/None contribution means automatic non-negative surplus).
"""
    try:
        p = parse_financial_profile(profile).to_profile_dict()
    except (ValueError, TypeError) as exc:
        raise ScenarioInputError(f"FinancialProfile không đúng schema: {exc}") from exc
    if not isinstance(assumptions, dict):
        raise ScenarioInputError("assumptions phải là dict.")
    unknown = set(assumptions) - ENGINE_ASSUMPTIONS
    if unknown:
        raise ScenarioInputError(f"Assumptions chưa được hỗ trợ: {sorted(unknown)}")
    a = deepcopy(assumptions)
    for field in ("monthly_primary_income", "monthly_other_income", "monthly_essential_expense",
                  "monthly_discretionary_expense", "monthly_debt_payment", "current_savings",
                  "emergency_fund_reserved", "goal_amount"):
        finite_number(p[field], field, 0)
    if p["goal_amount"] <= 0:
        raise ScenarioInputError("goal_amount phải lớn hơn 0.")
    n = p["goal_horizon_months"]
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 120:
        raise ScenarioInputError("goal_horizon_months phải là số nguyên 1–120.")
    if p["risk_tolerance"] not in ("low", "medium", "high"):
        raise ScenarioInputError("Cần xác nhận risk_tolerance trước khi mô phỏng.")
    if p["liquidity_need"] not in ("low", "medium", "high"):
        raise ScenarioInputError("Cần xác nhận liquidity_need trước khi mô phỏng.")
    cfg = load_scenario_defaults()
    limits = cfg["limits"]
    rate = finite_number(a.get("annual_return_rate"), "annual_return_rate")
    cap = limits["max_annual_return_rate_by_risk"][p["risk_tolerance"]]
    if not limits["min_annual_return_rate"] <= rate <= cap:
        raise ScenarioInputError(f"annual_return_rate ngoài giới hạn mô phỏng "
                                 f"[{limits['min_annual_return_rate']}, {cap}] cho {p['risk_tolerance']}.")
    inflation = finite_number(a.get("annual_inflation_rate", 0.0), "annual_inflation_rate")
    if not limits["min_annual_inflation_rate"] <= inflation <= limits["max_annual_inflation_rate"]:
        raise ScenarioInputError("annual_inflation_rate ngoài giới hạn mô phỏng.")
    if a.get("monthly_contribution") is not None:
        finite_number(a["monthly_contribution"], "monthly_contribution", 0)
    maximum = a.get("max_projection_months", 1200)
    if isinstance(maximum, bool) or not isinstance(maximum, int) or not n <= maximum <= limits["max_projection_months"]:
        raise ScenarioInputError("max_projection_months phải >= thời hạn và <= 1200.")
    return p, a


def call_engine(profile: dict, assumptions: dict) -> dict:
    """Call the public Person 2 API; wrap expected numeric errors consistently."""
    try:
        result = calculate_financial_metrics(deepcopy(profile), deepcopy(assumptions))
        if not all(math.isfinite(result[k]) for k in ("fv_total", "adjusted_goal_amount", "goal_gap")):
            raise ValueError("Kết quả vượt giới hạn số hữu hạn.")
        return result
    except (CalculationInputError, TypeError, ValueError, OverflowError) as exc:
        raise ScenarioInputError(f"Không thể tính kết quả: {exc}") from exc


def project_scenario(profile: dict, assumptions: dict, *, name: str, label: str) -> dict:
    """Return engine metrics and monthly series for one checked constant scenario.

Every projected balance/target is obtained from the public calculation engine;
no FV formula or private Person 2 helper is copied here. Raises ScenarioInputError.
"""
    result = call_engine(profile, assumptions)
    rows = [{"month": 0, "balance": result["initial_available_amount"],
             "target_amount": profile["goal_amount"], "monthly_contribution": 0.0,
             "cumulative_contributions": 0.0}]
    for month in range(1, profile["goal_horizon_months"] + 1):
        p, a = deepcopy(profile), deepcopy(assumptions)
        p["goal_horizon_months"] = month
        a["max_projection_months"] = 1  # Only FV/target is used for this point.
        point = call_engine(p, a)
        rows.append({"month": month, "balance": point["fv_total"],
                     "target_amount": point["adjusted_goal_amount"],
                     "monthly_contribution": point["monthly_contribution"],
                     "cumulative_contributions": point["monthly_contribution"] * month})
    warnings = list(result["calculation_warnings"])
    warnings.append("income_growth_not_applied_in_mvp")
    return {
        "scenario_name": name, "label": label,
        "profile_used": deepcopy(profile), "assumptions": deepcopy(assumptions),
        "calculation_result": result, "monthly_projection": rows,
        "total_contributions": rows[-1]["cumulative_contributions"],
        "investment_gain": result["fv_total"] - result["initial_available_amount"] - rows[-1]["cumulative_contributions"],
        "emergency_fund_reserved": profile["emergency_fund_reserved"],
        "emergency_fund_available": min(profile["current_savings"], profile["emergency_fund_reserved"]),
        "warnings": warnings,
    }


def build_scenarios(profile: dict, base_assumptions: dict) -> dict:
    """Build conservative/base/optimistic dictionaries from a shared profile.

Input: 15-key FinancialProfile and annual decimal engine assumptions.
Output: each scenario has calculation_result, monthly_projection, assumptions,
profile_used, totals and warnings; metadata describes the hypothetical defaults.
Raises ScenarioInputError for invalid inputs, config or calculation errors.
The final application's caller must perform validation and human confirmation.
"""
    p, a = prepare_inputs(profile, base_assumptions)
    cfg = load_scenario_defaults()
    result: dict[str, Any] = {}
    for name in SCENARIO_NAMES:
        spec = cfg["scenarios"][name]
        sp, sa = deepcopy(p), deepcopy(a)
        for field in ("monthly_primary_income", "monthly_other_income"):
            sp[field] *= spec["income_multiplier"]
        sp["monthly_discretionary_expense"] *= spec["discretionary_expense_multiplier"]
        requested_rate = a["annual_return_rate"] + spec["annual_return_rate_offset"]
        limits = cfg["limits"]
        sa["annual_return_rate"] = min(
            max(requested_rate, limits["min_annual_return_rate"]),
            limits["max_annual_return_rate_by_risk"][p["risk_tolerance"]])
        if name != "base":
            available = call_engine(sp, sa)
            if a.get("monthly_contribution") is None:
                # With automatic mode, save at most all of the adjusted surplus.
                sa["monthly_contribution"] = available["affordable_monthly_contribution"] * min(spec["contribution_multiplier"], 1.0)
            else:
                sa["monthly_contribution"] = a["monthly_contribution"] * spec["contribution_multiplier"]
        item = project_scenario(sp, sa, name=name, label=spec["label"])
        item["scenario_adjustments"] = deepcopy(spec)
        item["requested_annual_return_rate"] = requested_rate
        if not math.isclose(requested_rate, sa["annual_return_rate"], abs_tol=1e-12):
            item["warnings"].append("scenario_return_rate_clipped_to_demo_limit")
        result[name] = item
    result["metadata"] = {
        "currency": "VND", "rate_basis": "annual_effective",
        "income_growth_applied": False,
        "assumption_source": "config/scenario_defaults.json; educational assumptions, not market data",
        "limits": deepcopy(cfg["limits"]), "is_final_plan": False,
    }
    return result


def run_what_if(profile: dict, base_assumptions: dict,
                profile_updates: dict | None = None, assumption_updates: dict | None = None) -> dict:
    """Return baseline/modified/comparison without mutating source inputs.

Only documented numeric cash-flow/goal fields and public engine options may be
updated. Setting monthly_contribution=None selects automatic surplus mode.
Explicit contributions stay explicit when income/expenses change; affordability
warnings are retained. Raises ScenarioInputError for invalid/unknown changes.
"""
    p, a = prepare_inputs(profile, base_assumptions)
    pu = {} if profile_updates is None else profile_updates
    au = {} if assumption_updates is None else assumption_updates
    if not isinstance(pu, dict) or not isinstance(au, dict):
        raise ScenarioInputError("Các thay đổi what-if phải là dict.")
    if set(pu) - WHAT_IF_PROFILE_FIELDS or set(au) - ENGINE_ASSUMPTIONS:
        raise ScenarioInputError("What-if chứa tên trường không được hỗ trợ.")
    changed_p, changed_a = deepcopy(p), deepcopy(a)
    changed_p.update(deepcopy(pu))
    changed_a.update(deepcopy(au))
    changed_p, changed_a = prepare_inputs(changed_p, changed_a)
    baseline = project_scenario(p, a, name="baseline", label="Trước thay đổi")
    modified = project_scenario(changed_p, changed_a, name="what_if", label="Sau thay đổi")
    before, after = baseline["calculation_result"], modified["calculation_result"]
    old_month, new_month = before["estimated_month_to_goal"], after["estimated_month_to_goal"]
    return {
        "baseline": baseline, "modified": modified,
        "changes": {"profile_updates": deepcopy(pu), "assumption_updates": deepcopy(au)},
        "comparison": {
            "fv_total_change": after["fv_total"] - before["fv_total"],
            "goal_gap_change": after["goal_gap"] - before["goal_gap"],
            "month_to_goal_change": None if old_month is None or new_month is None else new_month - old_month,
            "horizons_differ": p["goal_horizon_months"] != changed_p["goal_horizon_months"],
        },
        "is_final_plan": False,
    }
