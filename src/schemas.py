"""Shared data schemas for Project 09.

This module belongs to Person 1.  It defines the structural contract for a
financial profile, but intentionally does not implement business validation.
Rules such as positive income, a 1--120 month horizon, negative cash flow, or
cross-field consistency belong to ``src.validation`` (Person 4).

Internal conventions
--------------------
* Monetary values are numeric VND amounts without thousands separators.
* Rates are annual decimal values (for example, 5% is represented as 0.05).
* Goal horizon is an integer number of months.
* Information that was not supplied is represented by ``None``, never by an
  invented zero.
"""

from __future__ import annotations

import math
from typing import Annotated, Any, Literal, Mapping, TypeAlias

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictStr


PROFILE_FIELD_NAMES: tuple[str, ...] = (
    "user_id",
    "monthly_primary_income",
    "monthly_other_income",
    "monthly_essential_expense",
    "monthly_discretionary_expense",
    "monthly_debt_payment",
    "current_savings",
    "emergency_fund_reserved",
    "goal_name",
    "goal_amount",
    "goal_horizon_months",
    "risk_tolerance",
    "liquidity_need",
    "expected_income_growth",
    "notes",
)

RiskLevel: TypeAlias = Literal["low", "medium", "high"]
LiquidityLevel: TypeAlias = Literal["low", "medium", "high"]


def _parse_nullable_number(value: Any) -> float | None:
    """Accept a finite JSON number or ``None`` without accepting booleans/strings.

    Negative values remain structurally valid so the validation module can
    return a controlled, user-facing business error instead of failing during
    deserialization.
    """

    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("value must be a JSON number or null")

    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("value must be finite")
    return parsed


def _parse_nullable_month_count(value: Any) -> int | None:
    """Accept an integer month count or ``None`` without coercing other types."""

    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("goal_horizon_months must be an integer or null")
    return value


NullableNumber: TypeAlias = Annotated[
    float | None,
    BeforeValidator(_parse_nullable_number),
]
NullableMonthCount: TypeAlias = Annotated[
    int | None,
    BeforeValidator(_parse_nullable_month_count),
]


class FinancialProfile(BaseModel):
    """Canonical Project 09 financial-profile schema.

    Every agreed key is required to be present in an input mapping.  A key can
    contain ``None`` when the user did not supply the corresponding value.  As
    a result, downstream modules always receive the same 15-key shape and can
    distinguish missing information from an explicitly supplied zero.

    Raises:
        pydantic.ValidationError: If a key is missing, an extra key is present,
            a value has the wrong structural type, or a level is outside
            ``low``, ``medium``, and ``high``.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    user_id: StrictStr | None = Field(
        ...,
        description="Synthetic/session user identifier; never a real personal ID.",
    )
    monthly_primary_income: NullableNumber = Field(
        ...,
        description="Primary monthly income in VND.",
    )
    monthly_other_income: NullableNumber = Field(
        ...,
        description="Other monthly income in VND.",
    )
    monthly_essential_expense: NullableNumber = Field(
        ...,
        description="Essential monthly expense in VND.",
    )
    monthly_discretionary_expense: NullableNumber = Field(
        ...,
        description="Discretionary monthly expense in VND.",
    )
    monthly_debt_payment: NullableNumber = Field(
        ...,
        description="Monthly debt payment in VND.",
    )
    current_savings: NullableNumber = Field(
        ...,
        description="Current savings in VND.",
    )
    emergency_fund_reserved: NullableNumber = Field(
        ...,
        description="Savings reserved as an emergency fund in VND.",
    )
    goal_name: StrictStr | None = Field(
        ...,
        description="User-facing name of the primary financial goal.",
    )
    goal_amount: NullableNumber = Field(
        ...,
        description="Target amount in VND.",
    )
    goal_horizon_months: NullableMonthCount = Field(
        ...,
        description="Goal horizon as an integer number of months.",
    )
    risk_tolerance: RiskLevel | None = Field(
        ...,
        description="Risk tolerance: low, medium, high, or null.",
    )
    liquidity_need: LiquidityLevel | None = Field(
        ...,
        description="Liquidity need: low, medium, high, or null.",
    )
    expected_income_growth: NullableNumber = Field(
        ...,
        description="Expected annual income-growth rate as a decimal.",
    )
    notes: StrictStr | None = Field(
        ...,
        description="Optional user-supplied context; null when unavailable.",
    )

    def to_profile_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible 15-key dictionary in canonical field order.

        Returns:
            A newly allocated dictionary. ``None`` values are preserved.

        Raises:
            No application-level errors. Pydantic may raise a validation error
            earlier if invalid data is assigned to the model.
        """

        return self.model_dump(mode="json", exclude_none=False)


def parse_financial_profile(profile: Mapping[str, Any]) -> FinancialProfile:
    """Parse a mapping into :class:`FinancialProfile` without mutating it.

    Args:
        profile: Mapping containing exactly the 15 agreed profile keys.

    Returns:
        A validated ``FinancialProfile`` instance.

    Raises:
        TypeError: If ``profile`` is not a mapping.
        pydantic.ValidationError: If the mapping violates the structural
            FinancialProfile contract.
    """

    if not isinstance(profile, Mapping):
        raise TypeError("profile must be a mapping")
    return FinancialProfile.model_validate(dict(profile))


def get_financial_profile_json_schema() -> dict[str, Any]:
    """Return a fresh JSON Schema dictionary for LLM structured output.

    Returns:
        JSON Schema generated from ``FinancialProfile``.

    Raises:
        No expected application-level errors.
    """

    return FinancialProfile.model_json_schema()


__all__ = [
    "FinancialProfile",
    "LiquidityLevel",
    "NullableMonthCount",
    "NullableNumber",
    "PROFILE_FIELD_NAMES",
    "RiskLevel",
    "get_financial_profile_json_schema",
    "parse_financial_profile",
]
