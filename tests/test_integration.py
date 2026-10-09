"""End-to-end backend contracts for the five integrated owner modules."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pypdf import PdfReader

from src.llm_explanation import ExplanationError, generate_explanation
from src.report_generator import generate_report
from src.scenarios import build_scenarios
from src.stress_test import run_stress_test
from src.validation import validate_profile


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def profiles() -> dict[str, dict]:
    cases = json.loads((ROOT / "data" / "test_cases.json").read_text(encoding="utf-8"))["cases"]
    return {case["case_id"]: case["expected_profile"] for case in cases}


def _final_bundle(profile: dict) -> tuple[dict, dict, dict]:
    assumptions = {"annual_return_rate": 0.0}
    validation = validate_profile(profile, assumptions)
    assert validation["status"] in {"VALID", "WARNING"}
    assert validation["can_simulate"] is True
    scenarios = build_scenarios(profile, assumptions)
    final_assumptions = scenarios["base"]["assumptions"]
    final_validation = validate_profile(profile, final_assumptions)
    assert final_validation["status"] in {"VALID", "WARNING"}
    assert final_validation["can_simulate"] is True
    return scenarios, scenarios["base"]["calculation_result"], final_validation


def test_p001_runs_from_profile_to_confirmed_pdf(profiles, tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    profile = profiles["P001"]
    scenarios, calculation, validation = _final_bundle(profile)
    scenario_result = {
        "scenarios": scenarios,
        "what_if": None,
        "stress_test": None,
        "is_final_plan": False,
    }
    explanation = generate_explanation(profile, calculation, scenario_result, validation)
    assert "118.000.000 VND" in explanation
    assert "ngoại tuyến" in explanation
    target = tmp_path / "p001.pdf"
    generated = generate_report(profile, {
        "calculation_result": calculation,
        "scenario_result": scenario_result,
        "validation_result": validation,
        "profile_confirmed": True,
        "assumptions_confirmed": True,
        "report_confirmed": True,
    }, explanation, str(target))
    assert Path(generated).is_file()
    assert len(PdfReader(generated).pages) >= 1


def test_p009_missing_horizon_is_blocked_before_calculation(profiles):
    profile = profiles["P009"]
    validation = validate_profile(profile, {"annual_return_rate": 0.0})
    assert validation["status"] == "NEEDS_CLARIFICATION"
    assert validation["can_simulate"] is False
    assert "goal_horizon_months" in validation["missing_fields"]
    with pytest.raises(ExplanationError):
        generate_explanation(profile, {}, {}, validation)


def test_p019_stress_is_consistent_and_reportable(profiles, tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    profile = profiles["P019"]
    scenarios, calculation, validation = _final_bundle(profile)
    assumptions = scenarios["base"]["assumptions"]
    stress = run_stress_test(profile, assumptions, {
        "income_reduction_rate": 0.20,
        "start_month": 1,
        "duration_months": 3,
    })
    assert calculation["fv_total"] == pytest.approx(130_000_000)
    assert stress["stressed"]["calculation_result"]["fv_total"] == pytest.approx(118_000_000)
    assert stress["comparison"]["goal_delay_months"] == 3
    assert stress["comparison"]["extension_months_from_original_horizon"] == 1
    scenario_result = {
        "scenarios": scenarios,
        "what_if": None,
        "stress_test": stress,
        "is_final_plan": False,
    }
    explanation = generate_explanation(profile, calculation, scenario_result, validation)
    target = tmp_path / "p019.pdf"
    generate_report(profile, {
        "calculation_result": calculation,
        "scenario_result": scenario_result,
        "validation_result": validation,
        "profile_confirmed": True,
        "assumptions_confirmed": True,
        "report_confirmed": True,
    }, explanation, str(target))
    assert target.stat().st_size > 500


def test_streamlit_app_starts_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    assert not app.exception
    assert any("Goal-Based Personal Finance Planner" in title.value for title in app.title)
