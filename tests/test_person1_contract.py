"""Contract tests for Person 1's FinancialProfile schema."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from src.schemas import (
    PROFILE_FIELD_NAMES,
    FinancialProfile,
    get_financial_profile_json_schema,
    parse_financial_profile,
)


def make_valid_profile() -> dict[str, Any]:
    """Return one complete synthetic profile using the shared contract."""

    return {
        "user_id": "P001",
        "monthly_primary_income": 8_000_000,
        "monthly_other_income": 2_000_000,
        "monthly_essential_expense": 5_000_000,
        "monthly_discretionary_expense": 2_000_000,
        "monthly_debt_payment": 0,
        "current_savings": 15_000_000,
        "emergency_fund_reserved": 5_000_000,
        "goal_name": "Học cao học",
        "goal_amount": 100_000_000,
        "goal_horizon_months": 36,
        "risk_tolerance": "low",
        "liquidity_need": "medium",
        "expected_income_growth": 0.05,
        "notes": "Hồ sơ hoàn toàn giả lập.",
    }


def test_valid_profile_round_trip_and_input_is_not_mutated() -> None:
    payload = make_valid_profile()
    original = deepcopy(payload)

    profile = parse_financial_profile(payload)
    result = profile.to_profile_dict()

    assert payload == original
    assert tuple(result) == PROFILE_FIELD_NAMES
    assert len(result) == 15
    assert result["monthly_primary_income"] == 8_000_000.0
    assert result["expected_income_growth"] == 0.05
    assert result["risk_tolerance"] == "low"


def test_explicit_zero_is_preserved() -> None:
    profile = parse_financial_profile(make_valid_profile())

    assert profile.monthly_debt_payment == 0.0


def test_missing_information_is_preserved_as_none() -> None:
    payload = make_valid_profile()
    payload["goal_horizon_months"] = None
    payload["expected_income_growth"] = None
    payload["notes"] = None

    result = parse_financial_profile(payload).to_profile_dict()

    assert result["goal_horizon_months"] is None
    assert result["expected_income_growth"] is None
    assert result["notes"] is None


def test_every_agreed_key_must_be_present_even_when_value_is_unknown() -> None:
    payload = make_valid_profile()
    del payload["goal_amount"]

    with pytest.raises(ValidationError, match="goal_amount"):
        parse_financial_profile(payload)


@pytest.mark.parametrize("field", ["risk_tolerance", "liquidity_need"])
def test_level_outside_contract_is_rejected(field: str) -> None:
    payload = make_valid_profile()
    payload[field] = "very_high"

    with pytest.raises(ValidationError):
        parse_financial_profile(payload)


@pytest.mark.parametrize(
    "invalid_value",
    ["8000000", True, float("nan"), float("inf"), float("-inf")],
)
def test_non_numeric_or_non_finite_money_is_rejected(invalid_value: object) -> None:
    payload = make_valid_profile()
    payload["monthly_primary_income"] = invalid_value

    with pytest.raises(ValidationError):
        parse_financial_profile(payload)


@pytest.mark.parametrize("invalid_value", ["36", 36.0, True])
def test_goal_horizon_is_not_coerced_to_integer(invalid_value: object) -> None:
    payload = make_valid_profile()
    payload["goal_horizon_months"] = invalid_value

    with pytest.raises(ValidationError):
        parse_financial_profile(payload)


def test_unknown_field_is_rejected() -> None:
    payload = make_valid_profile()
    payload["full_name"] = "Không được lưu dữ liệu định danh"

    with pytest.raises(ValidationError, match="full_name"):
        parse_financial_profile(payload)


def test_non_mapping_input_raises_controlled_type_error() -> None:
    with pytest.raises(TypeError, match="profile must be a mapping"):
        parse_financial_profile([])  # type: ignore[arg-type]


def test_business_rule_values_are_left_for_validation_module() -> None:
    payload = make_valid_profile()
    payload["monthly_primary_income"] = -1
    payload["goal_horizon_months"] = 0

    profile = parse_financial_profile(payload)

    assert profile.monthly_primary_income == -1.0
    assert profile.goal_horizon_months == 0


def test_json_schema_has_exact_required_profile_keys() -> None:
    schema = get_financial_profile_json_schema()

    assert tuple(schema["properties"]) == PROFILE_FIELD_NAMES
    assert set(schema["required"]) == set(PROFILE_FIELD_NAMES)
    assert schema["additionalProperties"] is False


def test_direct_model_assignment_is_validated() -> None:
    profile = FinancialProfile.model_validate(make_valid_profile())

    with pytest.raises(ValidationError):
        profile.risk_tolerance = "invalid"  # type: ignore[assignment]
