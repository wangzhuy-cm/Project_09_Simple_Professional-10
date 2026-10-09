"""Data-integrity and UI-helper tests for Person 1's module."""

from __future__ import annotations

import csv
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.schemas import PROFILE_FIELD_NAMES, parse_financial_profile
from ui.profile_page import (
    MockExtractionError,
    PROFILE_DRAFT_SESSION_KEY,
    build_manual_profile,
    load_mock_cases,
    mock_extract_profile,
    parse_optional_integer_input,
    parse_optional_number_input,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_PATH = DATA_DIR / "sample_profiles.csv"
EXPECTED_PATH = DATA_DIR / "expected_results.csv"
TEST_CASES_PATH = DATA_DIR / "test_cases.json"
VALID_EXAMPLE_PATH = DATA_DIR / "example_profile_valid.json"
MISSING_EXAMPLE_PATH = DATA_DIR / "example_profile_missing.json"

EXPECTED_CATEGORY_COUNTS = {
    "valid_feasible": 5,
    "valid_infeasible": 3,
    "missing_information": 3,
    "contradictory": 3,
    "negative_cashflow": 2,
    "out_of_scope": 2,
    "stress_test": 2,
}

NUMERIC_FIELDS = {
    "monthly_primary_income",
    "monthly_other_income",
    "monthly_essential_expense",
    "monthly_discretionary_expense",
    "monthly_debt_payment",
    "current_savings",
    "emergency_fund_reserved",
    "goal_amount",
    "expected_income_growth",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read one UTF-8 CSV fixture without silently accepting extra cells."""

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert all(None not in row for row in rows)
    return rows


def _profile_from_csv_row(row: Mapping[str, str]) -> dict[str, Any]:
    """Convert canonical CSV cells to the shared Python profile types."""

    profile: dict[str, Any] = {}
    for field in PROFILE_FIELD_NAMES:
        raw_value = row[field].strip()
        if not raw_value:
            profile[field] = None
        elif field in NUMERIC_FIELDS:
            profile[field] = float(raw_value)
        elif field == "goal_horizon_months":
            profile[field] = int(raw_value)
        else:
            profile[field] = raw_value
    return parse_financial_profile(profile).to_profile_dict()


def _json_payload() -> dict[str, Any]:
    with TEST_CASES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_csv_and_json_files_are_readable_with_expected_row_count() -> None:
    sample_rows = _read_csv(SAMPLE_PATH)
    expected_rows = _read_csv(EXPECTED_PATH)
    payload = _json_payload()

    assert len(sample_rows) == 20
    assert len(expected_rows) == 20
    assert len(payload["cases"]) == 20

    # Explicitly demonstrate that the CSV files are also DataFrame-compatible.
    assert pd.read_csv(SAMPLE_PATH).shape[0] == 20
    assert pd.read_csv(EXPECTED_PATH).shape[0] == 20


def test_category_distribution_matches_project_plan() -> None:
    payload = _json_payload()

    counts = Counter(case["category"] for case in payload["cases"])

    assert counts == EXPECTED_CATEGORY_COUNTS


def test_case_ids_are_unique_and_aligned_across_all_files() -> None:
    sample_ids = [row["case_id"] for row in _read_csv(SAMPLE_PATH)]
    expected_ids = [row["case_id"] for row in _read_csv(EXPECTED_PATH)]
    json_ids = [case["case_id"] for case in _json_payload()["cases"]]

    assert len(set(sample_ids)) == 20
    assert sample_ids == expected_ids == json_ids
    assert sample_ids == [f"P{number:03d}" for number in range(1, 21)]


def test_all_json_ground_truth_profiles_follow_shared_schema() -> None:
    for case in _json_payload()["cases"]:
        profile = parse_financial_profile(case["expected_profile"]).to_profile_dict()
        # ``notes`` is optional context and is not counted as a missing
        # financial field in the ground-truth manifest.
        actual_null_fields = [
            field
            for field in PROFILE_FIELD_NAMES
            if field != "notes" and profile[field] is None
        ]

        assert tuple(profile) == PROFILE_FIELD_NAMES
        assert profile["user_id"] == case["case_id"]
        assert actual_null_fields == case["expected_null_fields"]


def test_csv_profiles_and_json_ground_truth_are_identical() -> None:
    sample_rows = {
        row["case_id"]: row for row in _read_csv(SAMPLE_PATH)
    }
    expected_rows = {
        row["case_id"]: row for row in _read_csv(EXPECTED_PATH)
    }

    for case in _json_payload()["cases"]:
        case_id = case["case_id"]
        expected_profile = parse_financial_profile(
            case["expected_profile"]
        ).to_profile_dict()

        assert sample_rows[case_id]["natural_language_input"] == case["input_text"]
        assert sample_rows[case_id]["case_category"] == case["category"]
        assert expected_rows[case_id]["case_category"] == case["category"]
        assert _profile_from_csv_row(sample_rows[case_id]) == expected_profile
        assert _profile_from_csv_row(expected_rows[case_id]) == expected_profile


def test_expected_null_field_column_matches_json_manifest() -> None:
    expected_rows = {
        row["case_id"]: row for row in _read_csv(EXPECTED_PATH)
    }

    for case in _json_payload()["cases"]:
        raw_fields = expected_rows[case["case_id"]]["expected_null_fields"]
        csv_fields = raw_fields.split(";") if raw_fields else []
        assert csv_fields == case["expected_null_fields"]


def test_data_contains_no_direct_identifier_columns() -> None:
    sample_columns = set(_read_csv(SAMPLE_PATH)[0])
    forbidden_columns = {
        "full_name",
        "name",
        "phone",
        "email",
        "address",
        "cccd",
        "bank_account",
    }

    assert sample_columns.isdisjoint(forbidden_columns)
    assert all(
        case["expected_profile"]["user_id"].startswith("P")
        for case in _json_payload()["cases"]
    )


def test_handoff_json_examples_match_ground_truth_cases() -> None:
    cases = {case["case_id"]: case for case in _json_payload()["cases"]}

    with VALID_EXAMPLE_PATH.open(encoding="utf-8") as handle:
        valid_example = json.load(handle)
    with MISSING_EXAMPLE_PATH.open(encoding="utf-8") as handle:
        missing_example = json.load(handle)

    assert parse_financial_profile(valid_example).to_profile_dict() == (
        parse_financial_profile(cases["P001"]["expected_profile"]).to_profile_dict()
    )
    assert parse_financial_profile(missing_example).to_profile_dict() == (
        parse_financial_profile(cases["P009"]["expected_profile"]).to_profile_dict()
    )
    assert missing_example["goal_horizon_months"] is None


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [("", None), ("  ", None), ("0", 0.0), ("8000000", 8_000_000.0), ("-1", -1.0)],
)
def test_optional_number_parser(raw_value: str, expected: float | None) -> None:
    assert parse_optional_number_input(raw_value) == expected


@pytest.mark.parametrize("raw_value", ["8,000,000", "8.000.000", "abc", "1e6"])
def test_optional_number_parser_rejects_non_contract_formats(raw_value: str) -> None:
    with pytest.raises(ValueError):
        parse_optional_number_input(raw_value)


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [("", None), ("36", 36), ("0", 0), ("-1", -1)],
)
def test_optional_integer_parser(raw_value: str, expected: int | None) -> None:
    assert parse_optional_integer_input(raw_value) == expected


@pytest.mark.parametrize("raw_value", ["36.0", "3 years", "abc"])
def test_optional_integer_parser_rejects_non_integer_values(raw_value: str) -> None:
    with pytest.raises(ValueError):
        parse_optional_integer_input(raw_value)


def test_manual_form_builder_returns_canonical_profile_without_mutating_input() -> None:
    values = {
        "user_id": " DEMO_01 ",
        "monthly_primary_income": "8000000",
        "monthly_other_income": "2000000",
        "monthly_essential_expense": "5000000",
        "monthly_discretionary_expense": "2000000",
        "monthly_debt_payment": "0",
        "current_savings": "15000000",
        "emergency_fund_reserved": "5000000",
        "goal_name": " Học cao học ",
        "goal_amount": "100000000",
        "goal_horizon_months": "36",
        "risk_tolerance": "low",
        "liquidity_need": "medium",
        "expected_income_growth": "0.05",
        "notes": " ",
    }
    original = deepcopy(values)

    profile = build_manual_profile(values)

    assert values == original
    assert tuple(profile) == PROFILE_FIELD_NAMES
    assert profile["user_id"] == "DEMO_01"
    assert profile["monthly_primary_income"] == 8_000_000.0
    assert profile["notes"] is None


def test_manual_form_builder_keeps_blank_fields_as_none() -> None:
    profile = build_manual_profile({})

    assert tuple(profile) == PROFILE_FIELD_NAMES
    assert all(value is None for value in profile.values())


def test_mock_loader_and_extractor_return_independent_copies() -> None:
    cases = load_mock_cases(TEST_CASES_PATH)
    original = deepcopy(cases[0]["expected_profile"])

    first_result = mock_extract_profile(cases[0]["input_text"], cases)
    first_result["goal_amount"] = 1
    second_result = mock_extract_profile(cases[0]["input_text"], cases)

    assert len(cases) == 20
    assert cases[0]["expected_profile"] == original
    assert second_result["goal_amount"] == 100_000_000.0


def test_mock_extractor_rejects_unknown_text() -> None:
    with pytest.raises(MockExtractionError):
        mock_extract_profile("Đây không phải mô tả có trong dữ liệu mẫu.")


def test_profile_page_renders_without_runtime_exception() -> None:
    app = AppTest.from_string(
        "from ui.profile_page import render_profile_page\nrender_profile_page()"
    )

    app.run(timeout=15)

    assert not app.exception
    assert len(app.header) == 1
    assert len(app.radio) == 1
    assert app.radio[0].value == "Nhập thủ công"


def test_profile_page_mock_extraction_flow_returns_canonical_profile() -> None:
    app = AppTest.from_string(
        "from ui.profile_page import render_profile_page\nrender_profile_page()"
    ).run(timeout=15)

    app.radio[0].set_value("Mô tả tự nhiên").run(timeout=15)
    app.button[0].click().run(timeout=15)

    assert not app.exception
    assert not app.error
    assert len(app.success) == 1
    rendered_profile = app.session_state[PROFILE_DRAFT_SESSION_KEY]
    assert tuple(rendered_profile) == PROFILE_FIELD_NAMES
    assert rendered_profile["user_id"] == "P001"
    assert rendered_profile["goal_amount"] == 100_000_000.0


def test_profile_page_does_not_save_an_empty_ai_extraction() -> None:
    source = (
        "from ui.profile_page import render_profile_page\n"
        "from src.schemas import PROFILE_FIELD_NAMES\n"
        "def empty_extractor(text):\n"
        "    return {field: None for field in PROFILE_FIELD_NAMES}\n"
        "render_profile_page(empty_extractor)\n"
    )
    app = AppTest.from_string(source).run(timeout=15)
    app.radio[0].set_value("Mô tả tự nhiên").run(timeout=15)
    app.button[0].click().run(timeout=15)

    assert not app.exception
    assert app.error
    assert "chưa được lưu" in app.error[0].value.lower()
    assert PROFILE_DRAFT_SESSION_KEY not in app.session_state
