"""Reproduce offline sample reports. Run from the project root."""
from pathlib import Path
import sys
import json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.scenarios import build_scenarios, run_what_if
from src.stress_test import run_stress_test
from src.validation import validate_profile
from src.market_reference import reference_assumptions
from src.llm_explanation import generate_explanation_result
from src.report_generator import generate_report

ROOT = Path(__file__).resolve().parents[1]
cases = json.loads((ROOT / "data/test_cases.json").read_text(encoding="utf-8"))["cases"]
for case_id in ("P001", "P019"):
    profile = next(c["expected_profile"] for c in cases if c["case_id"] == case_id)
    assumptions = reference_assumptions() if case_id == "P001" else {"annual_return_rate": 0.0}
    scenarios = build_scenarios(profile, assumptions)
    output = {"scenarios": scenarios,
        "what_if": run_what_if(profile, assumptions, {"monthly_primary_income": profile["monthly_primary_income"] + 1000000}),
        "stress_test": run_stress_test(profile, assumptions, {"income_reduction_rate": .2, "duration_months": 3, "start_month": 1})}
    calculation = scenarios["base"]["calculation_result"]
    validation = validate_profile(profile, assumptions)
    text = generate_explanation_result(profile, calculation, output, validation, use_llm=False)["text"]
    result = {"calculation_result": calculation, "scenario_result": output, "validation_result": validation,
              "profile_confirmed": True, "assumptions_confirmed": True, "report_confirmed": True}
    target = ROOT / "docs" / f"QA_{case_id}_report.pdf"
    generate_report(profile, result, text, str(target))
    if case_id == "P001":
        generate_report(profile, result, text, str(ROOT / "outputs/sample_report.pdf"))
    print(target)
